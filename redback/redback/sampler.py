import os
import sys
from pathlib import Path

import bilby

import pandas as pd

from . import afterglow

from .result import RedbackResult
from .utils import find_path, logger
from .model_library import all_models_dict
from .likelihoods import GRBGaussianLikelihood, GaussianLikelihood, PoissonLikelihood

dirname = os.path.dirname(__file__)


def fit_model(name, path, model, source_type='GRB', sampler='dynesty', nlive=2000, prior=None, walks=200,
              truncate=True, use_photon_index_prior=False, truncate_method='prompt_time_error', data_mode='flux',
              resume=True, save_format='json', **kwargs):
    """

    Parameters
    ----------
    :param source_type: 'GRB', 'Supernova', 'TDE', 'Prompt', 'Kilonova'
    :param name: Telephone number of transient, e.g., GRB 140903A
    :param path: Path to the data folder which contains transient data files, if using inbuilt data files then 'GRBData'
    :param model: String to indicate which model to fit to data
    :param sampler: String to indicate which sampler to use, default is dynesty
    and nested samplers are encouraged to allow evidence calculation
    :param nlive: number of live points
    :param prior: if Prior is true user needs to pass a dictionary with priors defined the bilby way
    :param walks: number of walkers
    :param truncate: flag to confirm whether to truncate the prompt emission data
    :param use_photon_index_prior: flag to turn off/on photon index prior and fits according to the curvature effect
    :param truncate_method: method of truncation
    :param data_mode: 'luminosity', 'flux', 'flux_density', depending on which kind of data will be accessed
    :param resume:
    :param save_format:
    :param kwargs: additional parameters that will be passed to the sampler
    :return: bilby result object, transient specific data object
    """
    if source_type.upper() in ['GRB', 'SGRB', 'LGRB']:
        return _fit_grb(name=name, path=path, model=model, sampler=sampler, nlive=nlive, prior=prior, walks=walks,
                        truncate=truncate, use_photon_index_prior=use_photon_index_prior,
                        truncate_method=truncate_method, data_mode=data_mode, resume=resume,
                        save_format=save_format, **kwargs)
    elif source_type.upper() in ['KILONOVA']:
        return _fit_kilonova(name=name, path=path, model=model, sampler=sampler, nlive=nlive, prior=prior, walks=walks,
                             truncate=truncate, use_photon_index_prior=use_photon_index_prior,
                             truncate_method=truncate_method, data_mode=data_mode, resume=resume,
                             save_format=save_format, **kwargs)
    elif source_type.upper() in ['PROMPT']:
        return _fit_prompt(name=name, path=path, model=model, sampler=sampler, nlive=nlive, prior=prior, walks=walks,
                           truncate=truncate, use_photon_index_prior=use_photon_index_prior,
                           truncate_method=truncate_method, data_mode=data_mode, resume=resume,
                           save_format=save_format, **kwargs)
    elif source_type.upper() in ['SUPERNOVA']:
        return _fit_supernova(name=name, path=path, model=model, sampler=sampler, nlive=nlive, prior=prior,
                              walks=walks, truncate=truncate, use_photon_index_prior=use_photon_index_prior,
                              truncate_method=truncate_method, data_mode=data_mode,
                              resume=resume, save_format=save_format, **kwargs)
    elif source_type.upper() in ['TDE']:
        return _fit_tde(name=name, path=path, model=model, sampler=sampler, nlive=nlive, prior=prior, walks=walks,
                        truncate=truncate, use_photon_index_prior=use_photon_index_prior,
                        truncate_method=truncate_method, data_mode=data_mode,
                        resume=resume, save_format=save_format, **kwargs)
    else:
        raise ValueError(f'Source type {source_type} not known')


def _fit_grb(name, path, model, sampler='dynesty', nlive=3000, prior=None, walks=1000, truncate=True,
             use_photon_index_prior=False, truncate_method='prompt_time_error', data_mode='flux', data=None,
             resume=True, save_format='json', **kwargs):
    if data is None:
        data = afterglow.SGRB(name, data_mode=data_mode)
        data.load_and_truncate_data(truncate=truncate, truncate_method=truncate_method, data_mode=data_mode)

    if prior is None:
        prior = bilby.prior.PriorDict(filename=f"{dirname}/Priors/{model}.prior")

    if use_photon_index_prior:
        if data.photon_index < 0.:
            logger.info('photon index for GRB', data.name, 'is negative. Using default prior on alpha_1')
            prior['alpha_1'] = bilby.prior.Uniform(-10, -0.5, 'alpha_1', latex_label=r'$\alpha_{1}$')
        else:
            prior['alpha_1'] = bilby.prior.Gaussian(mu=-(data.photon_index + 1), sigma=0.1,
                                                    latex_label=r'$\alpha_{1}$')

    if isinstance(model, str):
        function = all_models_dict[model]
    else:
        function = model

    outdir = f"{find_path(path)}/GRB{name}/{model}"
    Path(outdir).mkdir(parents=True, exist_ok=True)

    label = data_mode
    if use_photon_index_prior:
        label += '_photon_index'
    likelihood = GRBGaussianLikelihood(x=data.x, y=data.y, sigma=data.y_err, function=function)

    meta_data = dict(model=model, transient=data, path=path, use_photon_index_prior=use_photon_index_prior,
                     truncate=truncate, truncate_method=truncate_method, save_format=save_format)

    result = bilby.run_sampler(likelihood=likelihood, priors=prior, label=label, sampler=sampler, nlive=nlive,
                               outdir=outdir, plot=True, use_ratio=False, walks=walks, resume=resume,
                               maxmcmc=10 * walks, result_class=RedbackResult, meta_data=meta_data,
                               nthreads=4, save_bounds=False, nsteps=nlive, nwalkers=walks, save=save_format, **kwargs)

    return result, data


def _fit_kilonova(**kwargs):
    pass


def _fit_prompt(**kwargs):
    pass


def _fit_supernova(**kwargs):
    pass


def _fit_tde(**kwargs):
    pass
