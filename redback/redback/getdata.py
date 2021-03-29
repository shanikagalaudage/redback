"""
Code for reading GRB data from Swift website
"""
import os
import sys
import time
import urllib
import urllib.request
import requests

import pandas as pd
import numpy as np
import astropy.units as uu

from .utils import logger, fetch_driver, check_element, calc_fluxdensity_from_ABmag, calc_flux_density_error
from .redback_errors import DataExists, WebsiteExist

from bilby.core.utils import check_directory_exists_and_if_not_mkdir
from astropy.time import Time

dirname = os.path.dirname(__file__)

SWIFT_PROMPT_BIN_SIZES = ['1s', '2ms', '8ms', '16ms', '64ms', '256ms']


def afterglow_directory_structure(grb, use_default_directory, data_mode, instrument='BAT+XRT'):
    if use_default_directory:
        grb_dir = os.path.join(dirname, '../data/GRBData/GRB' + grb + '/afterglow/')
    else:
        grb_dir = 'GRBData/GRB' + grb + '/afterglow/'

    grb_dir = grb_dir + data_mode + '/'
    check_directory_exists_and_if_not_mkdir(grb_dir)

    rawfile_path = grb_dir + 'GRB' + grb

    if instrument == 'xrt':
        rawfile = rawfile_path + '_xrt_rawSwiftData.csv'
        fullfile = rawfile_path + '_xrt_csv'
        logger.warning('You are only downloading XRT data, you may not capture the tail of the prompt emission.')
    else:
        logger.warning('You are downloading BAT and XRT data, you will need to truncate the data for some models.')
        rawfile = rawfile_path + '_rawSwiftData.csv'
        fullfile = rawfile_path + '.csv'

    return grb_dir, rawfile, fullfile


def prompt_directory_structure(grb, use_default_directory, bin_size='2ms'):
    if bin_size not in SWIFT_PROMPT_BIN_SIZES:
        raise ValueError(f'Bin size {bin_size} not in allowed bin sizes.\n'
                         f'Use one of the following: {SWIFT_PROMPT_BIN_SIZES}')
    if use_default_directory:
        grb_dir = os.path.join(dirname, '../data/GRBData/GRB' + grb + '/')
    else:
        grb_dir = 'GRBData/GRB' + grb + '/'

    grb_dir = grb_dir + 'prompt/'
    check_directory_exists_and_if_not_mkdir(grb_dir)

    rawfile_path = grb_dir + f'{bin_size}_lc_ascii.dat'
    processed_file_path = grb_dir + f'{bin_size}_lc.csv'
    return grb_dir, rawfile_path, processed_file_path


def process_fluxdensity_data(grb, rawfile):
    logger.info('Getting trigger number')
    trigger = get_trigger_number(grb)
    grb_website = 'http://www.swift.ac.uk/burst_analyser/00' + trigger + '/'
    logger.info('opening Swift website for GRB {}'.format(grb))

    # open the webdriver
    driver = fetch_driver()

    driver.get(grb_website)
    try:
        driver.find_element_by_xpath("//select[@name='xrtsub']/option[text()='no']").click()
        time.sleep(20)
        driver.find_element_by_id("xrt_DENSITY_makeDownload").click()
        time.sleep(20)
        grb_url = driver.current_url

        # Close the driver and all opened windows
        driver.quit()

        # scrape the data
        urllib.request.urlretrieve(grb_url, rawfile)
        logger.info(f'Congratulations, you now have raw data for GRB {grb}')
    except Exception:
        logger.warning('cannot load the website for GRB {}'.format(grb))


def process_integrated_flux_data(grb, rawfile):
    logger.info('Getting trigger number')
    trigger = get_trigger_number(grb)
    grb_website = 'http://www.swift.ac.uk/burst_analyser/00' + trigger + '/'
    logger.info('opening Swift website for GRB {}'.format(grb))

    # open the webdriver
    driver = fetch_driver()

    driver.get(grb_website)

    # celect option for BAT bin_size
    bat_binning = 'batxrtbin'
    if check_element(driver, bat_binning):
        driver.find_element_by_xpath("//select[@name='batxrtbin']/option[text()='SNR 4']").click()

    # select option for subplot
    subplot = "batxrtsub"
    if check_element(driver, subplot):
        driver.find_element_by_xpath("//select[@name='batxrtsub']/option[text()='no']").click()

    # Select option for flux density
    flux_density1 = "batxrtband1"
    flux_density0 = "batxrtband0"
    if (check_element(driver, flux_density1)) and (check_element(driver, flux_density0)):
        driver.find_element_by_xpath(".//*[@id='batxrtband1']").click()
        driver.find_element_by_xpath(".//*[@id='batxrtband0']").click()

    # Generate data file
    driver.find_element_by_xpath(".//*[@id='batxrt_XRTBAND_makeDownload']").click()
    time.sleep(20)

    grb_url = driver.current_url

    # Close the driver and all opened windows
    driver.quit()

    # scrape the data
    urllib.request.urlretrieve(grb_url, rawfile)
    logger.info('Congratulations, you now have raw data for GRB {}'.format(grb))

def sort_integrated_flux_data(rawfile, fullfile):
    xrtpcflag = 0
    xrtpc = []

    batflag = 0
    bat = []

    xrtwtflag = 0
    xrtwt = []

    try:
        with open(rawfile) as data:
            for num, line in enumerate(data):
                if line[0] == '!':
                    if line[2:13] == 'batSNR4flux':
                        xrtpcflag = 0
                        batflag = 1
                        xrtwtflag = 0
                    elif line[2:11] == 'xrtpcflux':
                        xrtpcflag = 1
                        batflag = 0
                        xrtwtflag = 0
                    elif line[2:11] == 'xrtwtflux':
                        xrtpcflag = 0
                        batflag = 0
                        xrtwtflag = 1
                    else:
                        xrtpcflag = 0
                        batflag = 0
                        xrtwtflag = 0

                if xrtpcflag == 1:
                    xrtpc.append(line)
                if batflag == 1:
                    bat.append(line)
                if xrtwtflag == 1:
                    xrtwt.append(line)

        with open(fullfile, 'w') as out:
            out.write('## BAT - batSNR4flux\n')
            for ii in range(len(bat)):
                try:
                    int(bat[ii][0])
                    out.write(bat[ii])
                except ValueError:
                    pass

            out.write('\n')
            out.write('## XRT - xrtwtflux\n')
            for ii in range(len(xrtwt)):
                try:
                    int(xrtwt[ii][0])
                    out.write(xrtwt[ii])
                except ValueError:
                    pass

            out.write('\n')
            out.write('## XRT - xrtpcflux\n')

            for ii in range(len(xrtpc)):
                try:
                    int(xrtpc[ii][0])
                    out.write(xrtpc[ii])
                except ValueError:
                    pass
    except IOError:
        try:
            logger.warning('There was an error opening the file')
            sys.exit()
        except SystemExit:
            pass
    logger.info('Congratulations, you now have a nice data file: {}'.format(fullfile))


def sort_fluxdensity_data(rawfile, fullfile):
    logger.info('Congratulations, you now have a nice data file: {}'.format(fullfile))


def collect_swift_data(grb, use_default_directory, data_mode):
    valid_data_modes = ['flux', 'flux_density']
    if data_mode not in valid_data_modes:
        raise ValueError("Swift does not have {} data".format(data_mode))

    grbdir, rawfile, fullfile = afterglow_directory_structure(grb, use_default_directory, data_mode)

    if os.path.isfile(rawfile):
        logger.warning('The raw data file already exists')
        return grbdir, rawfile, fullfile

    logger.info('Getting trigger number')
    trigger = get_trigger_number(grb)
    grb_website = 'http://www.swift.ac.uk/burst_analyser/00' + trigger + '/'
    logger.info('opening Swift website for GRB {}'.format(grb))
    response = requests.get(grb_website)
    if 'No Light curve available' in response.text:
        logger.warning('Problem loading the website for GRB {}. Are you sure GRB {} has Swift data?'.format(grb, grb))
        raise WebsiteExist('Problem loading the website for GRB {}'.format(grb))
    else:
        if data_mode == 'flux':
            process_integrated_flux_data(grb, rawfile)
        if data_mode == 'flux_density':
            process_fluxdensity_data(grb, rawfile)

    return rawfile, fullfile

def sort_swift_data(rawfile, fullfile, data_mode):
    if os.path.isfile(fullfile):
        logger.warning('The processed data file already exists')
        return None

    if not os.path.isfile(rawfile):
        logger.warning('The raw data does not exist.')
        raise DataExists('Raw data is missing.')

    if data_mode == 'flux':
        sort_integrated_flux_data(rawfile, fullfile)
    if data_mode == 'flux_density':
        sort_fluxdensity_data(rawfile, fullfile)
    return None

def get_afterglow_data_from_swift(grb, data_mode = 'flux',use_default_directory=False):
    rawfile, fullfile = collect_swift_data(grb, use_default_directory, data_mode)
    sort_swift_data(rawfile, fullfile, data_mode)
    return None

def get_xrt_data_from_swift(grb, data_mode = 'flux',use_default_directory=False):
    grbdir, rawfile, fullfile = afterglow_directory_structure(grb, use_default_directory, data_mode, instrument='xrt')
    logger.info('Getting trigger number')
    trigger = get_trigger_number(grb)
    grb_website = 'https://www.swift.ac.uk/xrt_curves/00'+trigger+'/flux.qdp'
    response = requests.get(grb_website)
    if 'No Light curve available' in response.text:
        logger.warning('Problem loading the website for GRB {}. Are you sure GRB {} has Swift data?'.format(grb, grb))
        raise WebsiteExist('Problem loading the website for GRB {}'.format(grb))

    urllib.request.urlretrieve(grb_website, rawfile)
    logger.info('Congratulations, you now have raw XRT data for GRB {}'.format(grb))
    data = process_xrt_data(rawfile)
    data.to_csv(fullfile, sep=',', index=False)
    logger.info('Congratulations, you now have processed XRT data for GRB {}'.format(grb))
    return None

def process_xrt_data(rawfile):
    data = np.loadtxt(rawfile, comments=['!', 'READ', 'NO'])
    time = data[:, 0]
    timepos = data[:, 1]
    timeneg = data[:, 2]
    flux = data[:, 3]
    fluxpos = data[:, 4]
    fluxneg = data[:, 5]
    data = {'time': time, 'timepos': timepos, 'timeneg': timeneg,
            'flux': flux, 'fluxpos': fluxpos, 'fluxneg': fluxneg}
    data = pd.DataFrame(data)
    processedfile = data[data['fluxpos'] != 0.]
    return processedfile


def collect_swift_prompt_data(grb, use_default_directory=False, bin_size='2ms'):
    grbdir, rawfile, processed_file = prompt_directory_structure(
        grb=grb, use_default_directory=use_default_directory, bin_size=bin_size)
    if os.path.isfile(rawfile):
        logger.warning('The raw data file already exists')
        return None

    if not grb.startswith('GRB'):
        grb = 'GRB' + grb

    grb_website = f"https://swift.gsfc.nasa.gov/results/batgrbcat/{grb}/data_product/"
    logger.info('opening Swift website for GRB {}'.format(grb))
    data_file = f"{bin_size}_lc_ascii.dat"

    # open the webdriver
    driver = fetch_driver()

    driver.get(grb_website)
    try:
        driver.find_element_by_partial_link_text("results").click()
        time.sleep(20)
        driver.find_element_by_link_text("lc/").click()
        time.sleep(20)
        grb_url = driver.current_url + data_file
        urllib.request.urlretrieve(grb_url, rawfile)

        # Close the driver and all opened windows
        driver.quit()

        logger.info(f'Congratulations, you now have raw data for GRB {grb}')
    except Exception:
        logger.warning(f'Cannot load the website for GRB {grb}')


def sort_swift_prompt_data(grb, use_default_directory):
    grbdir, rawfile_path, processed_file_path = prompt_directory_structure(grb, use_default_directory)

    if os.path.isfile(processed_file_path):
        logger.warning('The processed data file already exists')
        return pd.read_csv(processed_file_path, sep='\t')

    if not os.path.isfile(rawfile_path):
        logger.warning('The raw data does not exist.')
        raise DataExists('Raw data is missing.')

    data = np.loadtxt(rawfile_path)
    df = pd.DataFrame(data=data, columns=[
        "Time [s]", "flux_15_25 [counts/s/det]", "flux_15_25_err [counts/s/det]", "flux_25_50 [counts/s/det]",
        "flux_25_50_err [counts/s/det]", "flux_50_100 [counts/s/det]", "flux_50_100_err [counts/s/det]",
        "flux_100_350 [counts/s/det]", "flux_100_350_err [counts/s/det]", "flux_15_350 [counts/s/det]",
        "flux_15_350_err [counts/s/det]"])
    df.to_csv(processed_file_path, index=False)
    return df


def get_prompt_data_from_swift(grb, bin_size='2ms', use_default_directory=False):
    collect_swift_prompt_data(grb=grb, use_default_directory=use_default_directory, bin_size=bin_size)
    data = sort_swift_prompt_data(grb=grb, use_default_directory=use_default_directory)
    return data


def get_prompt_data_from_fermi(grb):
    return None


def get_prompt_data_from_konus(grb):
    return None


def get_prompt_data_from_batse(grb):
    return None


def get_open_transient_catalog_data(transient, transient_type, use_default_directory=False):
    collect_open_catalog_data(transient, use_default_directory, transient_type)
    data = sort_open_access_data(transient, use_default_directory, transient_type)
    return data


def transient_directory_structure(transient, use_default_directory, transient_type):
    if use_default_directory:
        open_transient_dir = os.path.join(dirname, '../data/' + transient_type + 'Data/' + transient + '/')
    else:
        open_transient_dir = transient_type + '/' + transient + '/'
    rawfile_path = open_transient_dir + transient + '_rawdata.csv'
    fullfile_path = open_transient_dir + transient + '_data.csv'
    return open_transient_dir, rawfile_path, fullfile_path


def collect_open_catalog_data(transient, use_default_directory, transient_type):
    transient_dict = ['kilonova', 'supernova', 'tidal_disruption_event']

    open_transient_dir, raw_filename, full_filename = transient_directory_structure(transient, use_default_directory,
                                                                                    transient_type)

    check_directory_exists_and_if_not_mkdir(open_transient_dir)

    if os.path.isfile(raw_filename):
        logger.warning('The raw data file already exists')
        return None

    if transient_type not in transient_dict:
        logger.warning('Transient type does not have open access data')
        raise WebsiteExist()
    url = 'https://api.astrocats.space/' + transient + '/photometry/time+magnitude+e_magnitude+band+system?e_magnitude&band&time&format=csv&complete'
    response = requests.get(url)

    if 'not found' in response.text:
        logger.warning(
            'Transient {} does not exist in the catalog. Are you sure you are using the right alias?'.format(transient))
        raise WebsiteExist('Webpage does not exist')
    else:
        if os.path.isfile(full_filename):
            logger.warning('The processed data file already exists')
            return None
        else:
            metadata = open_transient_dir + 'metadata.csv'
            urllib.request.urlretrieve(url, raw_filename)
            logger.info('Retrieved data for {}'.format(transient))
            metadataurl = 'https://api.astrocats.space/'+ transient + '/timeofmerger+discoverdate+redshift+ra+dec+host?format=CSV'
            urllib.request.urlretrieve(metadataurl, metadata)
            logger.info('Metdata for transient {} added'.format(transient))

def get_t0_from_grb(transient):
    if np.isnan(timeofevent):
        logger.warning('Not found an associated GRB. Temporarily using the first data point as a start time')
        logger.warning('Please run function fix_t0_of_transient before any further analysis')
    return timeofevent

def fix_t0_of_transient(timeofevent, transient, transient_type, use_default_directory=False):
    """
    :param timeofevent: T0 of event in mjd
    :param transient: transient name
    :param use_default_directory:
    :param transient_type:
    :return: None, but fixes the processed data file
    """
    directory, rawfilename, fullfilename = transient_directory_structure(transient, use_default_directory,
                                                                         transient_type)
    data = pd.read_csv(fullfilename, sep=',')
    timeofevent = Time(timeofevent, format='mjd')
    tt = Time(np.asarray(data['time'], dtype=float), format='mjd')
    data['time (days)'] = (tt - timeofevent).to(uu.day)
    data.to_csv(fullfilename, sep=',', index=False)
    logger.info(f'Change input time : {fullfilename}')
    return None


def sort_open_access_data(transient, use_default_directory, transient_type):
    directory, rawfilename, fullfilename = transient_directory_structure(transient, use_default_directory, transient_type)
    if os.path.isfile(fullfilename):
        logger.warning('processed data already exists')
        return pd.read_csv(fullfilename, sep=',')

    if not os.path.isfile(rawfilename):
        logger.warning('The raw data does not exist.')
        raise DataExists('Raw data is missing.')
    else:
        rawdata = pd.read_csv(rawfilename, sep = ',')
        logger.info('Processing data for transient {}.'.format(transient))
        data = rawdata
        data = data[data['band'] != 'C']
        data = data[data['band'] != 'W']
        data = data[data['system'] == 'AB']
        logger.info('Keeping only AB magnitude data')

        data['flux(mjy)'] = calc_fluxdensity_from_ABmag(data['magnitude'].values)
        data['flux_error'] = calc_flux_density_error(magnitude=data['magnitude'].values,
                                                     magnitude_error=data['e_magnitude'].values, reference_flux=3631, magnitude_system='AB')

        metadata = directory + 'metadata.csv'
        metadata = pd.read_csv(metadata)
        metadata.replace(r'^\s+$', np.nan, regex=True)
        timeofevent = metadata['timeofmerger'].iloc[0]

        if np.isnan(timeofevent) and transient_type == 'kilonova':
            logger.warning('No timeofevent in metadata. Looking through associated GRBs')
            timeofevent = get_t0_from_grb(transient)

        if np.isnan(timeofevent) and transient_type != 'kilonova':
            logger.warning('No time of event in metadata.')
            logger.warning('Temporarily using the first data point as a start time')
            logger.warning('Please run function fix_t0_of_transient before any further analysis')
            timeofevent = data['time'].iloc[0]

        timeofevent = Time(timeofevent, format='mjd')
        tt = Time(np.asarray(data['time'], dtype=float), format='mjd')
        data['time (days)'] = (tt - timeofevent).to(uu.day)
        data.to_csv(fullfilename, sep=',', index = False)
        logger.info(f'Congratulations, you now have a nice data file: {fullfilename}')
    return data


def get_trigger_number(grb):
    data = get_grb_table()
    trigger = data.query('GRB == @grb')['Trigger Number']
    if len(trigger) == 0:
        trigger = '0'
    else:
        trigger = trigger.values[0]
    return trigger


def get_grb_table():
    short_table = os.path.join(dirname, 'tables/SGRB_table.txt')
    sgrb = pd.read_csv(short_table, header=0,
                       error_bad_lines=False, delimiter='\t', dtype='str')
    long_table = os.path.join(dirname, 'tables/LGRB_table.txt')
    lgrb = pd.read_csv(long_table, header=0,
                       error_bad_lines=False, delimiter='\t', dtype='str')
    frames = [lgrb, sgrb]
    data = pd.concat(frames, ignore_index=True)
    return data
