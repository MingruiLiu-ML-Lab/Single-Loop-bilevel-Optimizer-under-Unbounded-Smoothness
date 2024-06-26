This is code for the ICML2024 paper "A Nearly Optimal Single Loop Algorithm for Stochastic Bilevel Optimization 
under Unbounded Smoothness"
## Abstract
This paper studies the problem of stochastic bilevel optimization where the upper-level function is nonconvex with potentially unbounded smoothness and the lower-level function is strongly convex. This problem is motivated by meta-learning applied to sequential data, such as text classification using recurrent neural networks, where the smoothness constant of the upper-level loss function
scales linearly with the gradient norm and can be potentially unbounded. Existing algorithm crucially relies on the nested loop design, which requires significant tuning efforts and is not practical. In this paper, we address this issue by proposing a Single Loop bIlevel oPtimizer (SLIP). The proposed algorithm first updates the lower-level variable by a few steps of stochastic gradient descent, and then simultaneously updates the upper-level variable by normalized stochastic gradient descent with momentum and the lower-level variable by stochastic gradient descent. Under standard assumptions, we show that our algorithm finds an $\epsilon$-stationary point within $\widetilde{\mathcal{O}}(1/\epsilon^4)$\footnote{Here $\widetilde{\mathcal{O}}(\cdot)$ compresses logarithmic factors of $1/\epsilon$ and $1/\delta$, where $\delta\in(0,1)$ denotes the failure probability.} oracle calls of stochastic gradient or Hessian-vector product, both in expectation and with high probability. This complexity result is nearly optimal up to logarithmic factors without mean-square smoothness of the stochastic gradient oracle. Our proof relies on (i) a refined characterization and control of the lower-level variable and (ii) establishing a novel connection between bilevel optimization and stochastic optimization under distributional drift. Our experiments on various tasks show that our algorithm significantly outperforms strong baselines in bilevel optimization.

We provide an example for running code for data hyper-cleaning on Sentiment140 set, which can be downloaded from https://huggingface.co/datasets/sentiment140, please put it in SLIP-main/data directory. 
###Requirements
PyTorch >= v1.6.0.

### Running code on Data Hyper-cleaning 
we set noise rate equal to 0.2 (set --noise_rate 0.4 for higher noise)

    python main.py --methods stocbio --data sentment140 --batch_size 512 --noise_rate 0.2 --inner_update_lr 5e-2 --outer_update_lr 5e-2 --hessian_lr 1e-1 --inner_update_step 3

    python main.py --methods ttsa    --data sentment140 --batch_size 512 --noise_rate 0.2 --inner_update_lr 5e-2 --outer_update_lr 1e-1 --hessian_lr 1e-1 --inner_update_step 1

    python main.py --methods f2sa    --data sentment140 --batch_size 512 --noise_rate 0.2 --inner_update_lr 5e-2 --outer_update_lr 5e-2 --lamb 5e-1 --incre_step 1e-1 --nu 5e-2 --inner_update_step 1

    python main.py --methods saba    --data sentment140 --batch_size 512 --noise_rate 0.2 --inner_update_lr 1e-1 --outer_update_lr 5e-2  --nu 1e-1 --inner_update_step 1

    python main.py --methods ma_soba --data sentment140 --batch_size 512 --noise_rate 0.2 --inner_update_lr 1e-1 --outer_update_lr 5e-2 --beta 0.9 --nu 1e-1 --inner_update_step 1

    python main.py --methods bo_rep  --data sentment140 --batch_size 512 --noise_rate 0.2 --inner_update_lr 5e-2 --outer_update_lr 5e-2 --grad_normalized  True --y_warm_start 3 --interval 2 --beta 0.9 --nu 1e-2 --inner_update_step 1

    python main.py --methods slip    --data sentment140 --batch_size 512 --noise_rate 0.2 --inner_update_lr 5e-2 --outer_update_lr 5e-2 --grad_normalized  True --y_warm_start 3 --interval 1 --beta 0.9 --nu 1e-2 --inner_update_step 1


