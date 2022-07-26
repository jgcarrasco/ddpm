import matplotlib.pyplot as plt

import torch
import torch.nn as nn

import utils


class ConditionalLinear(nn.Module):
    def __init__(self, num_in, num_out, n_steps):
        super(ConditionalLinear, self).__init__()
        self.num_out = num_out
        self.lin = nn.Linear(num_in, num_out)
        self.embed = nn.Embedding(n_steps, num_out)
        self.embed.weight.data.uniform_()

    def forward(self, x, y):
        out = self.lin(x)
        gamma = self.embed(y)
        out = gamma.view(-1, self.num_out) * out
        return out

class ConditionalModel(nn.Module):
    def __init__(self, n_steps):
        super(ConditionalModel, self).__init__()
        self.lin1 = ConditionalLinear(2, 128, n_steps)
        self.lin2 = ConditionalLinear(128, 128, n_steps)
        self.lin3 = ConditionalLinear(128, 4, n_steps)
        self.sigmoid = nn.Sigmoid()
    
    def forward(self, x, y):
        x = self.lin1(x, y)
        x = self.lin2(x, y)
        x = self.lin3(x, y)
        # Split into mu and sigma
        mu, sigma = torch.split(x, 2, dim=-1)
        # Pass sigma through a sigmoid layer in order to restrict it to [0, 1]
        sigma = self.sigmoid(sigma)
        return mu, sigma


class Diffusion:
    def __init__(self, model=None, timesteps=40):
        """
        Constructor for the diffusion class. The variance schedule of the
        forward diffusion process as well as another values derived from it
        will be precomputed and stored.

        Parameters
        ----------
        model : `nn.Module`
            Model used to predict the mean and stdev of the reversed diffusion
            process. It must return two tensors, mu and sigma, of the same
            shape of the input tensor. By default, a `ConditionalModel` is used.
        timesteps : int
            Number of timesteps for the diffusion process.
        """
        # Precompute betas and other values
        self.betas = utils.schedule_variances(timesteps=timesteps)
        self.alphas = 1 - self.betas
        self.alphas_cumprod = torch.cumprod(self.alphas, -1)
        self.alphas_cumprod_prev = torch.cat(
            [torch.tensor([1]).float(), 
             self.alphas_cumprod[:-1]], 0)
        self.sqrt_alphas_cumprod = torch.sqrt(self.alphas_cumprod)
        self.sqrt_one_minus_alphas_cumprod = torch.sqrt(1 - self.alphas_cumprod)

        self.timesteps = timesteps
        if model:
            self.model = model
        else:
            self.model = ConditionalModel(n_steps=timesteps)
    
    def sample_forward(self, x_0, t):
        """
        Implementation of the forward diffusion process from x_0 to x_t at 
        timestep t, q(x_t | x_0)

        Parameters
        ----------
        x_0 : `torch.Tensor`
            Tensor of shape (n_batch, 2), containing samples drawn from the
            original distribution.
        t : `torch.Tensor`
            Tensor of shape (n_batch, ), indicating from which timestep we
            want to sample, for every observation.

        Returns
        -------
        `torch.Tensor` of shape (n_batch, 2) containing the results of the 
        forward diffusion process.
        """
        z = torch.randn_like(x_0)
        return x_0 * self.sqrt_alphas_cumprod[t].unsqueeze(1) \
             + z * self.sqrt_one_minus_alphas_cumprod[t].unsqueeze(1)

    def compute_mu_posterior(self, x_0, x_t, t):
        """
        Compute the mean of the gaussian q(x_t-1 | x_t, x_0). This will be used
        when computing the loss.
        """
        pass
            
    #---------------
    # VISUALIZATION
    #---------------
    
    def plot_forward(self, x_0):
        """
        Plots the distribution at timesteps 0, T/2 and T, where T is the total
        number of timesteps.
        """

        x_Td2 = self.sample_forward(x_0, 
                                    torch.tensor([int((self.timesteps-1)/2)]))
        x_T = self.sample_forward(x_0, 
                                  torch.tensor([int(self.timesteps-1)]))

        fig, (ax1, ax2, ax3) = plt.subplots(ncols=3, figsize=(3*3, 3))
        ax1.scatter(x_0[:, 0], x_0[:, 1], alpha=0.5, s=5)
        ax1.set_title("t = " + str(0))
        ax2.scatter(x_Td2[:, 0], x_Td2[:, 1], alpha=0.5, s=5)
        ax2.set_title("t = " + str(int(self.timesteps/2)))
        ax3.scatter(x_T[:, 0], x_T[:, 1], alpha=0.5, s=5)
        ax3.set_title("t = " + str(self.timesteps))
        plt.show()
    
if __name__ == "__main__":
    diffusion = Diffusion()

    x_0 = utils.make_dataset()

    diffusion.plot_forward(x_0)

