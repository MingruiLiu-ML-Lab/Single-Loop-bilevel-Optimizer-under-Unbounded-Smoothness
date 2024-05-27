from torch import nn
from torch.nn import functional as F
from torch.utils.data import DataLoader, RandomSampler
from torch.optim import SGD
from copy import deepcopy
import gc
import torch
from sklearn.metrics import accuracy_score
import numpy as np
from .RNN_net import RNN
GLOVE_DIM=300
class Learner(nn.Module):
    """
    Meta Learner
    """
    def __init__(self, args, training_size):
        """
        :param args:
        """
        super(Learner, self).__init__()
        self.args = args
        self.num_labels = args.num_labels
        self.outer_update_lr  = args.outer_update_lr
        self.old_outer_update_lr = args.outer_update_lr
        self.inner_update_lr  = args.inner_update_lr
        self.inner_update_step = args.inner_update_step
        self.inner_update_step_eval = args.inner_update_step_eval
        self.training_size = training_size
        self.device =torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        self.inner_model = RNN(
                word_embed_dim=args.word_embed_dim,
                encoder_dim=args.encoder_dim,
                n_enc_layers=args.n_enc_layers,
                dpout_model=0.0,
                dpout_fc=0.0,
                fc_dim=args.fc_dim,
                n_classes=args.n_classes,
                pool_type=args.pool_type,
                linear_fc=args.linear_fc
            )
        self.lambda_x =  torch.ones((self.training_size)).to(self.device)
        self.lambda_x.requires_grad=True
        self.outer_optimizer = SGD([self.lambda_x], lr=self.outer_update_lr)
        self.inner_optimizer = SGD(self.inner_model.parameters(), lr=self.inner_update_lr)
        self.inner_stepLR = torch.optim.lr_scheduler.StepLR(self.inner_optimizer, step_size=args.epoch, gamma=0.8)
        self.outer_stepLR = torch.optim.lr_scheduler.StepLR(self.outer_optimizer, step_size=args.epoch, gamma=0.8)
        self.inner_model.train()
        self.gamma = args.gamma
        self.grad_clip = args.grad_clip
        self.no_meta = args.no_meta
        self.criterion = nn.CrossEntropyLoss(reduction='none').to(self.device)

    def forward(self, train_loader, training = True, epoch = 0):
        # self.model.load_state_dict(torch.load('checkpoints/itd-model.pkl'))
        task_accs = []
        task_loss = []
        sum_gradients = []
        num_inner_update_step = self.inner_update_step

        for step, data in enumerate(train_loader):
            self.inner_model.to(self.device)
            all_loss = []
            loss = torch.zeros(1).to(self.device)
            for i in range(0,num_inner_update_step):
                input, label_id, data_indx = next(iter(train_loader))
                outputs = predict(self.inner_model, input)
                loss = torch.mean(torch.sigmoid(self.lambda_x[data_indx])*self.criterion(outputs, label_id.to(self.device))) + 0.0001 * sum(
                        [x.norm().pow(2) for x in self.inner_model.parameters()]).sqrt()
                loss.backward()
                self.inner_optimizer.step()
            all_loss.append(loss.item())

            q_input, q_label_id,q_indx = data
            q_outputs = predict(self.inner_model, q_input)
            q_loss = torch.mean(self.criterion(q_outputs, q_label_id.to(self.device)))

            hypergradient = self.stocbio(self.args, q_loss, next(iter(train_loader)), next(iter(train_loader)))
            # print(f'Task loss: {np.mean(all_loss):.4f}')
            self.lambda_x.grad = hypergradient[0]
            grad_l2_norm_sq = torch.sum(self.lambda_x.grad * self.lambda_x.grad)
            grad_l2_norm = torch.sqrt(grad_l2_norm_sq).item()
            print(f"gradient norm: {grad_l2_norm}")
            self.outer_optimizer.step()
            self.outer_optimizer.zero_grad()

            self.inner_optimizer.zero_grad()
            q_logits = F.softmax(q_outputs, dim=1)
            pre_label_id = torch.argmax(q_logits, dim=1)
            pre_label_id = pre_label_id.detach().cpu().numpy().tolist()
            q_label_id = q_label_id.detach().cpu().numpy().tolist()

            acc = accuracy_score(pre_label_id, q_label_id)
            task_accs.append(acc)
            task_loss.append(q_loss.detach().cpu())
            torch.cuda.empty_cache()
            print(f'Task loss: {np.mean(task_loss):.4f}')

        self.inner_stepLR.step()
        self.outer_stepLR.step()

        return np.mean(task_accs), np.mean(task_loss)

    def collate_pad_(self, data_points):
        """ Pad data points with zeros to fit length of longest data point in batch. """
        s_embeds = data_points[0] if type(data_points[0])==list else  data_points[1]
        targets = data_points[1] if type(data_points[0])==list else  data_points[0]

        # Get sentences for batch and their lengths.
        s_lens = np.array([sent.shape[0] for sent in s_embeds])
        max_s_len = np.max(s_lens)
        # Encode sentences as glove vectors.
        bs = len(data_points[0])
        s_embed = np.zeros((max_s_len, bs, GLOVE_DIM))
        for i in range(bs):
            e = s_embeds[i]
            if len(e) <= 0:
                s_lens[i] = 1
            s_embed[: len(e), i] = e.copy()
        embeds = torch.from_numpy(s_embed).float().to(self.device)
        targets = torch.LongTensor(targets).to(self.device)
        return (embeds, s_lens), targets

    def test(self, test_loader):
        task_accs = []
        task_loss = []

        self.inner_model.to(self.device)
        for step, data in enumerate(test_loader):
            q_input, q_label_id, q_data_indx = data
            q_outputs = predict(self.inner_model, q_input)
            q_loss = torch.mean(self.criterion(q_outputs, q_label_id.to(self.device)))

            q_logits = F.softmax(q_outputs, dim=1)
            pre_label_id = torch.argmax(q_logits, dim=1)
            pre_label_id = pre_label_id.detach().cpu().numpy().tolist()
            q_label_id = q_label_id.detach().cpu().numpy().tolist()
            acc = accuracy_score(pre_label_id, q_label_id)
            task_accs.append(acc)
            task_loss.append(q_loss.detach().cpu())
            torch.cuda.empty_cache()
            print(f'Task loss: {np.mean(task_loss):.4f}, Task acc: {np.mean(task_accs):.4f}')
        return np.mean(task_accs), np.mean(task_loss)

    def stocbio(self, args, loss, query_batch, support_batch):
        train_data, train_labels, train_indx = support_batch
        val_data, val_labels, val_indx = query_batch
        Fy_gradient = torch.autograd.grad(loss, self.inner_model.parameters(), retain_graph=True)
        F_gradient = [g_param.view(-1) for g_param in Fy_gradient]
        v_0 = torch.unsqueeze(torch.reshape(torch.hstack(F_gradient), [-1]), 1).detach()

        # Fx_gradient = [g_param.view(-1) for g_param in Fx_gradient]

        # Hessian
        z_list = []
        outputs = predict(self.inner_model, train_data)
        loss = torch.mean(torch.sigmoid(self.lambda_x[train_indx])*self.criterion(outputs, train_labels.to(self.device))) + 0.0001 * sum(
                [x.norm().pow(2) for x in self.inner_model.parameters()]).sqrt()
        G_gradient = []
        Gy_gradient = torch.autograd.grad(loss, self.inner_model.parameters(), create_graph=True)

        for g_grad, param in zip(Gy_gradient, self.inner_model.parameters()):
            G_gradient.append((param - args.hessian_lr * g_grad).view(-1))
        G_gradient = torch.reshape(torch.hstack(G_gradient), [-1])

        for _ in range(args.hessian_q):
            Jacobian = torch.matmul(G_gradient, v_0)
            v_new = torch.autograd.grad(Jacobian, self.inner_model.parameters(), retain_graph=True)
            v_params = [v_param.view(-1) for v_param in v_new]
            v_0 = torch.unsqueeze(torch.reshape(torch.hstack(v_params), [-1]), 1).detach()
            z_list.append(v_0)
        v_Q = args.hessian_lr * v_0 + torch.sum(torch.stack(z_list), dim=0)

        # Gyx_gradient
        outputs = predict(self.inner_model, val_data)
        loss = torch.mean(torch.sigmoid(self.lambda_x[val_indx])*self.criterion(outputs, val_labels.to(self.device))) + 0.0001 * sum(
                [x.norm().pow(2) for x in self.inner_model.parameters()]).sqrt()
        Gy_gradient = torch.autograd.grad(loss, self.inner_model.parameters(), retain_graph=True, create_graph=True)
        Gy_params = [Gy_param.view(-1) for Gy_param in Gy_gradient]
        Gy_gradient_flat = torch.reshape(torch.hstack(Gy_params), [-1])
        Gyxv_gradient = torch.autograd.grad(-torch.matmul(Gy_gradient_flat, v_Q.detach()), self.lambda_x)
        outer_update =  Gyxv_gradient

        return outer_update


def predict(net, inputs):
    """ Get predictions for a single batch. """
    s_embed, s_lens = inputs
    outputs = net((s_embed.cuda(), s_lens))
    return outputs


