import numpy as np
import inspect

import bilby
from scipy.special import gammaln

class GaussianLikelihood(bilby.Likelihood):
    def __init__(self, x, y, sigma, function, kwargs):
        """
        A general Gaussian likelihood - the parameters are inferred from the
        arguments of function

        Parameters
        ----------
        x, y: array_like
            The data to analyse
        sigma: float
            The standard deviation of the noise
        function:
            The python function to fit to the data. Note, this must take the
            dependent variable as its first argument. The other arguments are
            will require a prior and will be sampled over (unless a fixed
            value is given).
        """
        self.x = x
        self.y = y
        self.sigma = sigma
        self.N = len(self.x)
        self.function = function
        self.kwargs = kwargs

        # These lines of code infer the parameters from the provided function
        parameters = inspect.getfullargspec(function).args
        parameters.pop(0)
        super().__init__(parameters=dict.fromkeys(parameters))

        self.function_keys = self.parameters.keys()
        if self.sigma is None:
            self.parameters['sigma'] = None

    def noise_log_likelihood(self):
        sigma = self.parameters.get('sigma', self.sigma)
        res = self.y - 0.
        log_l = np.sum(- (res / sigma) ** 2 / 2 -
                       np.log(2 * np.pi * sigma ** 2) / 2)
        self._noise_log_likelihood = log_l
        return self._noise_log_likelihood

    def log_likelihood(self):
        if self.kwargs != None:
            model = self.function(self.x, **self.parameters, **self.kwargs)
        else:
            model = self.function(self.x, **self.parameters)

        sigma = self.parameters.get('sigma', self.sigma)

        res = self.y - model
        log_l = np.sum(- (res / sigma) ** 2 / 2 -
                       np.log(2 * np.pi * sigma ** 2) / 2)
        return log_l


class GaussianLikelihood_quadrature_noise(bilby.Likelihood):
    def __init__(self, x, y, sigma_i, function, kwargs):
        """
        A general Gaussian likelihood - the parameters are inferred from the
        arguments of function

        Parameters
        ----------
        x, y: array_like
            The data to analyse
        sigma_i: float
            The standard deviation of the noise. This is part of the full noise.
            The sigma used in the likelihood is sigma = sqrt(sigma_i^2 + sigma^2)
        function:
            The python function to fit to the data. Note, this must take the
            dependent variable as its first argument. The other arguments are
            will require a prior and will be sampled over (unless a fixed
            value is given).
        """
        self.x = x
        self.y = y
        self.sigma_i = sigma_i
        self.N = len(self.x)
        self.function = function
        self.kwargs = kwargs

        # These lines of code infer the parameters from the provided function
        parameters = inspect.getfullargspec(function).args
        parameters.pop(0)
        super().__init__(parameters=dict.fromkeys(parameters))

        self.function_keys = self.parameters.keys()
        self.parameters['sigma'] = None

    def noise_log_likelihood(self):
        sigma_s = self.parameters['sigma']
        sigma = np.sqrt(self.sigma_i**2. + sigma_s**2.)
        res = self.y - 0.
        log_l = np.sum(- (res / sigma) ** 2 / 2 -
                       np.log(2 * np.pi * sigma ** 2) / 2)
        self._noise_log_likelihood = log_l
        return self._noise_log_likelihood

    def log_likelihood(self):
        if self.kwargs != None:
            model = self.function(self.x, **self.parameters, **self.kwargs)
        else:
            model = self.function(self.x, **self.parameters)

        sigma_s = self.parameters['sigma']
        sigma = np.sqrt(self.sigma_i**2. + sigma_s**2.)

        res = self.y - model
        log_l = np.sum(- (res / sigma) ** 2 / 2 -
                       np.log(2 * np.pi * sigma ** 2) / 2)
        return log_l


class GRBGaussianLikelihood(bilby.Likelihood):
    def __init__(self, x, y, sigma, function, kwargs):
        """
        A general Gaussian likelihood - the parameters are inferred from the
        arguments of function

        Parameters
        ----------
        x, y: array_like
            The data to analyse
        sigma: float
            The standard deviation of the noise
        function:
            The python function to fit to the data. Note, this must take the
            dependent variable as its first argument. The other arguments are
            will require a prior and will be sampled over (unless a fixed
            value is given).
        """
        self.x = x
        self.y = y
        self.sigma = sigma
        self.N = len(self.x)
        self.function = function
        self.kwargs = kwargs

        # These lines of code infer the parameters from the provided function
        parameters = inspect.getfullargspec(function).args
        parameters.pop(0)
        super().__init__(parameters=dict.fromkeys(parameters))

        self.function_keys = self.parameters.keys()
        if self.sigma is None:
            self.parameters['sigma'] = None

    def noise_log_likelihood(self):
        sigma = self.parameters.get('sigma', self.sigma)
        res = self.y - 0.
        log_l = np.sum(- (res / sigma) ** 2 / 2 -
                       np.log(2 * np.pi * sigma ** 2) / 2)
        self._noise_log_likelihood = log_l
        return self._noise_log_likelihood

    def log_likelihood(self):
        if self.kwargs != None:
            model = self.function(self.x, **self.parameters, **self.kwargs)
        else:
            model = self.function(self.x, **self.parameters)

        sigma = self.parameters.get('sigma', self.sigma)

        res = self.y - model
        log_l = np.sum(- (res / sigma) ** 2 / 2 -
                       np.log(2 * np.pi * sigma ** 2) / 2)
        return log_l


class PoissonLikelihood(bilby.Likelihood):
    def __init__(self, time, counts, function, kwargs):
        """
        Parameters
        ----------
        x, y: array_like
            The data to analyse
        background_rate: array_like
            The background rate
        function:
            The python function to fit to the data
        """
        self.time = time
        self.counts = counts
        self.function = function
        self.kwargs = kwargs
        self.dt = kwargs['dt']
        parameters = inspect.getfullargspec(function).args
        parameters.pop(0)
        self.parameters = dict.fromkeys(parameters)
        super(PoissonLikelihood, self).__init__(parameters=dict())

    def noise_log_likelihood(self):
        background_rate = self.parameters['bkg_rate'] * self.dt
        rate = 0 + background_rate
        log_l = np.sum(-rate + self.counts * np.log(rate) - gammaln(self.counts + 1))
        self._noise_log_likelihood = log_l
        return self._noise_log_likelihood

    def log_likelihood(self):
        if self.kwargs != None:
            rate = self.function(self.time, **self.parameters, **self.kwargs)
        else:
            rate = self.function(self.time, **self.parameters)

        logl = np.sum(-rate + self.counts * np.log(rate) - gammaln(self.counts + 1))
        return logl
