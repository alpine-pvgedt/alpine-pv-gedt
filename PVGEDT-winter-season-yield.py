# -*- coding: utf-8 -*-
"""
Created on Mon Aug 17 12:15:16 2026

@author: emily
"""

### disclosure: some code snippets from pvlib documentation:
### https://pvlib-python.readthedocs.io/en/stable/index.html


# import packages
import pandas as pd
import pvlib
import numpy as np


# import data classes and functions
from pvlib import clearsky
from datetime import timedelta

# define location constants
latitude = 46.838
longitude = 9.813
time_zone = 'Europe/Zurich'
altitude = 2490
name = 'Totalpsee'

# define PV module constants
surface_azimuth = 180 # due south
pv_module_area = 0.01169 # m^2
surface_tilt = 60
albedo = 0.796


#### FUNCTION TO ESTIMATE MONTHLY ENERGY YIELDS BASED ON LINEAR REGRESSION EQUATIONS ####

def estimate_monthly_yield(start_date,end_date):
 
    # define start and end dates of month in pandas dateTime format
    start_date = pd.to_datetime(start_date,dayfirst = True)
    end_date = pd.to_datetime(end_date,dayfirst=True)
    current_date = start_date
    
    # set up lists for the daily energy yields
    daily_baseline_yields = []
    daily_pvgedt_noloss_yields =[]
    daily_pvgedt_12pcloss_yields =[]
    
    while current_date <= end_date:     # iterate through the whole month
    
        # create time series for current day, with timestamps at 1-minute intervals
        today = current_date
        tomorrow = today + timedelta(days=1)
        times = pd.date_range(start=today, end=tomorrow, freq='1Min', tz=time_zone)
        
        # get solar position, airmass and Linke turbidity using pvlib
        solpos = pvlib.solarposition.get_solarposition(times, latitude, longitude, altitude)
        apparent_zenith = solpos['apparent_zenith']

        airmass = pvlib.atmosphere.get_relative_airmass(apparent_zenith)
        pressure = pvlib.atmosphere.alt2pres(altitude)
        airmass = pvlib.atmosphere.get_absolute_airmass(airmass, pressure)

        linke_turbidity = pvlib.clearsky.lookup_linke_turbidity(times, latitude, longitude)

        # get irradiance dataframe using ineichen & perez model from pvlib
        dni_extra = pvlib.irradiance.get_extra_radiation(times)
        ineichen = clearsky.ineichen(apparent_zenith, airmass, linke_turbidity, altitude, dni_extra)
        
        # get solar position components
        solar_zenith = solpos['zenith']
        solar_azimuth = solpos['azimuth']

        # get irradiance components
        dni = ineichen['dni']
        ghi = ineichen['ghi']
        dhi = ineichen['dhi']

        # get plane-of-array (POA) irradiance using pvlib
        poa_irradiance = pvlib.irradiance.get_total_irradiance(surface_tilt, surface_azimuth, solar_zenith, solar_azimuth, dni, ghi, dhi, dni_extra=None, airmass=None, albedo=albedo, surface_type=None, model='klucher', model_perez='allsitescomposite1990')
        
        # define baseline POA irradiance (not modified with topo sunrise/sunset times)
        poa_baseline = poa_irradiance['poa_global']

        # convert POA irradiances (W/m^2) into W, using the module cell area
        poa_baseline = poa_baseline.mul(pv_module_area)
        
        ######## get power output #######

        efficiency = 0.22 # assume efficiency is the STC value of 22\%
        power_baseline = poa_baseline.mul(efficiency)
        
        #### calculate daily energy yields for the baseline model using trapezoidal integration ###
        base_yield_daily = np.trapezoid(power_baseline,dx=1/60) # dx is the x-spacing (1 min intervals = 1/60 hours)

        ####### use the linear regression equations to estimate the PV-GEDT energy yield for the current day ######
                
        pvgedt_yield_daily_noloss = (1.389*base_yield_daily)-8.419
        pvgedt_yield_daily_12pcloss = (1.224*base_yield_daily)-7.432

        # append daily energy yields to appropriate lists
        daily_baseline_yields.append(base_yield_daily)
        daily_pvgedt_noloss_yields.append(pvgedt_yield_daily_noloss)
        daily_pvgedt_12pcloss_yields.append(pvgedt_yield_daily_12pcloss)
        
        # update the date
        current_date = tomorrow
        
    else:     # after the energy yield has been calculated for all dates in the month
        
        # sum the daily energy yields to find the monthly energy yield for each model
        monthly_baseline_yield = sum(daily_baseline_yields)
        monthly_pvgedt_noloss_yield = sum(daily_pvgedt_noloss_yields)
        monthly_pvgedt_12pcloss_yield = sum(daily_pvgedt_12pcloss_yields)
        
    return monthly_baseline_yield, monthly_pvgedt_noloss_yield, monthly_pvgedt_12pcloss_yield


########## FUNCTION TO CALCULATE ENERGY YIELD FOR EACH MONTH IN THE WINTER SEASON #########

def get_winter_season_yields ():
    oct_baseline_yield, oct_pvgedt_noloss_yield, oct_pvgedt_12pcloss_yield = estimate_monthly_yield('1/10/2023', '31/10/2023')
    nov_baseline_yield, nov_pvgedt_noloss_yield, nov_pvgedt_12pcloss_yield = estimate_monthly_yield('1/11/2023', '30/11/2023')
    dec_baseline_yield, dec_pvgedt_noloss_yield, dec_pvgedt_12pcloss_yield = estimate_monthly_yield('1/12/2023', '31/12/2023')
    jan_baseline_yield, jan_pvgedt_noloss_yield, jan_pvgedt_12pcloss_yield = estimate_monthly_yield('1/1/2024', '31/1/2024')
    feb_baseline_yield, feb_pvgedt_noloss_yield, feb_pvgedt_12pcloss_yield = estimate_monthly_yield('1/2/2024', '29/2/2024')
    mar_baseline_yield, mar_pvgedt_noloss_yield, mar_pvgedt_12pcloss_yield = estimate_monthly_yield('1/3/2024', '31/3/2024')
    
    # store monthly yields in a list
    monthly_baseline_yields=[oct_baseline_yield,nov_baseline_yield,dec_baseline_yield,jan_baseline_yield,feb_baseline_yield,mar_baseline_yield]
    monthly_pvgedt_noloss_yields = [oct_pvgedt_noloss_yield, nov_pvgedt_noloss_yield, dec_pvgedt_noloss_yield, jan_pvgedt_noloss_yield, feb_pvgedt_noloss_yield, mar_pvgedt_noloss_yield]
    monthly_pvgedt_12pcloss_yields = [oct_pvgedt_12pcloss_yield,nov_pvgedt_12pcloss_yield,dec_pvgedt_12pcloss_yield,jan_pvgedt_12pcloss_yield,feb_pvgedt_12pcloss_yield,mar_pvgedt_12pcloss_yield]
    
    return monthly_baseline_yields, monthly_pvgedt_noloss_yields, monthly_pvgedt_12pcloss_yields


###############################################################################
################################ MAIN CODE ####################################
###############################################################################

# get monthly energy yield for the entire winter season
baseline, pvgedt_noloss, pvgedt_12pcloss  = get_winter_season_yields()

# organise data and output as a csv file
months = ['October 2023', 'November 2023', 'December 2023', 'January 2024', 'February 2024', 'March 2024']
output_data = pd.DataFrame({'Date': months, 
                            'Baseline_Yield_Wh': baseline,
                            'PVGEDT_Yield_Nominal_Wh': pvgedt_noloss,
                            'PVGEDT_Yield_12pc_Loss_Wh': pvgedt_12pcloss})

output_data.to_csv('Monthly_Yield_Estimates_test.csv', index=False)
print('success')

