# -*- coding: utf-8 -*-
"""
Created on Wed Aug  5 01:24:29 2026

@author: emily
"""

# import packages
import matplotlib.pyplot as plt
import pandas as pd
import pvlib
import numpy as np
import pytz


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


# import topographical sunrise and sunset, panel tilt, and albedo values
input_data = pd.read_csv('input_data.csv',parse_dates = ['Date'],dayfirst=True)

#################### MAIN FUNCTION TO PLOT GRAPHS AND CALCULATE ENERGY YIELD ###################

# generative AI disclosure: function written/refactored with assistance from Claude Sonnet 4.6 via ELM portal
# this largely took the form of bug fixes and inspiration - at no point was the entire script copied from gen AI output

def calculate_energy_yield(date: str,topo_loss_factor, plot_irrad):
    
    # get row index of input_data csv file for the desired date
    row = input_data.loc[input_data['Date'] == date]
    row_index =  input_data.loc[input_data['Date'] == date].index.values.item()
    
    # define start and end timestamps (00:00 on the chosen date to 00:00 on the next day)
    start_date = row['Date'][row_index]
    end_date = start_date + timedelta(days=1)

    # create time series for this day, with timestamps at 1-minute intervals
    times = pd.date_range(start=start_date, end=end_date, freq='1Min', tz=time_zone)
    
    # extract the topographical sunrise times from the input_data csv file
    topo_sunrise = row['Topo_Sunrise'][row_index]
    sr_hours, sr_minutes = map(int, topo_sunrise.split(':'))
    
    # format as timestamp by including the date
    topo_sunrise = start_date + timedelta(hours=sr_hours, minutes=sr_minutes)
    
    # extract the topographical sunset times from the input_data csv file
    topo_sunset = row['Topo_Sunset'][row_index]
    ss_hours, ss_minutes = map(int, topo_sunset.split(':'))
    
    # format as timestamp by including the date
    topo_sunset = start_date + timedelta(hours=ss_hours, minutes=ss_minutes)
    
    # ensure timestamps are localised to the correct time zone (UTC+2 for daylight-savings, UTC+1 otherwise)
    topo_sunrise = pytz.timezone(time_zone).localize(topo_sunrise)
    topo_sunset = pytz.timezone(time_zone).localize(topo_sunset)
    
    # extract module surface tilt and ground albedo from input_data csv file
    surface_tilt = row['Panel_Tilt'][row_index]
    albedo = row['Albedo'][row_index]
    
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
    
    # get components of solar position
    solar_zenith = solpos['zenith']
    solar_azimuth = solpos['azimuth']

    # get irradiance components
    dni = ineichen['dni']
    ghi = ineichen['ghi']
    dhi = ineichen['dhi']

    # get plane-of-array (POA) irradiance using pvlib
    poa_irradiance = pvlib.irradiance.get_total_irradiance(surface_tilt, surface_azimuth, solar_zenith, solar_azimuth, dni, ghi, dhi, dni_extra=None, airmass=None, albedo=albedo, surface_type=None, model='klucher', model_perez='allsitescomposite1990')
    
    # get baseline POA irradiance (not modified with topo sunrise/sunset times)
    poa_baseline = poa_irradiance['poa_global']

    # get PV-GEDT POA irradiance by modifying baseline using topo sunrise and sunset times
    poa_pvgedt = poa_baseline.copy()

    for i in poa_pvgedt.index:
        if i < topo_sunrise:
            poa_pvgedt.loc[i] = 0              
        elif i > topo_sunset:
            poa_pvgedt.loc[i] = 0
            
    # convert POA irradiances into W (using the module cell area)
    poa_baseline = poa_baseline.mul(pv_module_area)
    poa_pvgedt = poa_pvgedt.mul(pv_module_area)
    
    ######## get power output #######

    efficiency = 0.22 # assume efficiency is the STC value of 22\%
    power_baseline = poa_baseline.mul(efficiency)
    power_pvgedt = poa_pvgedt.mul(efficiency)
    
    # add loss factor to the PV-GEDT model if desired (based on model fit to 13 Oct 2023)
    power_pvgedt = power_pvgedt.mul(1-topo_loss_factor)
    
    
    ####### make plots of baseline and PV-GEDT models #######
    
    fig,ax = plt.subplots()
    power_baseline.plot(ax = ax, color = 'darkviolet', linestyle = 'dashed', label = 'Baseline', linewidth = 2.5)
    power_pvgedt.plot(ax = ax, color = 'turquoise', label = 'PV-GEDT', linewidth = 2.5)

    ####### plot measured data #######
    
    # import measured power and irradiance data from correct csv file
    date_for_filename = start_date.strftime('%d-%b-%y').lower()
    power_filename = 'measured-power-' + date_for_filename + '.csv'
    measured_power = pd.read_csv(power_filename, parse_dates=True) 
    measured_power['Timestamp'] = pd.to_datetime(measured_power['Timestamp'], dayfirst = True) 
    
    irrad_filename = 'measured-irrad-' + date_for_filename + '.csv'
    measured_irradiance = pd.read_csv(irrad_filename, parse_dates=True)
    measured_irradiance['Timestamp'] = pd.to_datetime(measured_irradiance['Timestamp'], dayfirst = True)

    # plot measured power as a scatter plot on top of modelled power plots
    measured_power.plot.scatter(x = 'Timestamp', y = 'Pmpp_W', ax=ax, c = 'darkorange', label = 'Measured', s=50)
    
    # format axes labels and legend
    ax.set_xlabel('Timestamp (hh:mm)', fontsize = 15)
    ax.set_ylabel('Power Output (W)', fontsize = 15)
    ax.set_ybound(upper=4.2)
    ax.tick_params(axis='y', which='major', labelsize=12)
    ax.tick_params(axis='x', which='major', labelsize=12)
    ax.tick_params(axis='x', which='minor', labelsize=12)
    ax.legend(loc=2, prop ={'size':12});
    
    ###################### OPTIONAL PLOTS ################################
    
    ### optional: plot irradiance plots of PV-GEDT model and measured data
    
    if plot_irrad == True:
        fig2,ax2 = plt.subplots()
        
        dni_pvgedt = dni.copy()
        ghi_pvgedt = ghi.copy()
        for i in dni_pvgedt.index:
            if i < topo_sunrise:
                dni_pvgedt.loc[i] = 0  
                ghi_pvgedt.loc[i] = 0            
            elif i > topo_sunset:
                dni_pvgedt.loc[i] = 0
                ghi_pvgedt.loc[i] = 0
                
        dni_pvgedt.plot(ax = ax2, label = 'DNI: PV-GEDT\nmodel')
        ghi_pvgedt.plot(ax = ax2, label = 'GHI: PV-GEDT\nmodel')
        measured_irradiance.plot.scatter(x = 'Timestamp', y = 'Measured_DNI', ax = ax2, label = 'Measured DNI')
        measured_irradiance.plot.scatter(x = 'Timestamp', y = 'Measured_GHI', ax = ax2, c = 'darkorange', label = 'Measured GHI')
        
        # format axes labels and legend
        ax2.set_xlabel('Timestamp (hh:mm)', fontsize = 15)
        ax2.set_ylabel('Irradiance (W/m$^2$)', fontsize = 15)
        ax2.tick_params(axis='y', which='major', labelsize=12)
        ax2.tick_params(axis='x', which='major', labelsize=12)
        ax2.tick_params(axis='x', which='minor', labelsize=12)
        ax2.legend(loc=2, prop ={'size':10});

    ####### calculate energy yields #########

    #### calculate daily energy yields for the baseline and PV-GEDT models using trapezoidal integration ###
    base_yield_daily = np.trapezoid(power_baseline,dx=1/60) # dx is the x-spacing (1 min intervals = 1/60 hours)
    pvgedt_yield_daily = np.trapezoid(power_pvgedt,dx=1/60)
    
    ### calculate energy yield for the measured data over the period of measurement ###
   
    # get the energy yield using trapezoidal integration
    measured_power = measured_power.dropna() # remove rows with nan values of power
    power_measured = measured_power['Pmpp_W']
    
    # get the time intervals between measured data points (as they are irregularly spaced)
    measured_xs = measured_power['Timestamp']
    measurement_intervals = [0.0]
    current_value = 0.0
    
    # generative AI disclosure: for loop written with assistance from Llama 3.3 via ELM portal
    for i in range(len(measured_xs) - 1):
        interval = measured_xs[i+1] - measured_xs[i]
        next_value = current_value + ((interval.total_seconds())*1/3600)
        measurement_intervals.append(next_value)
        current_value = next_value
         
    m_yield = np.trapezoid(power_measured,measurement_intervals)
    
    ### calculate baseline and PV-GEDT yields only over the timespan of the measured data ###
    
    # get the time period
    t_start = min(measured_xs)
    t_start = pytz.timezone(time_zone).localize(t_start)
    t_end = max(measured_xs)
    t_end = pytz.timezone(time_zone).localize(t_end)
    
    # chop baseline power before and after the measurement period
    power_baseline_m = power_baseline.copy()
    power_baseline_m = power_baseline_m.truncate(t_start,t_end)
    
    # chop PV-GEDT power before and after the measurement period
    power_pvgedt_m = power_pvgedt.copy()
    power_pvgedt_m = power_pvgedt_m.truncate(t_start,t_end)
    
    # get model yields over the measured time period
    base_yield_m = np.trapezoid(power_baseline_m,dx=1/60) # dx ix x-spacing (1/60
    pvgedt_yield_m = np.trapezoid(power_pvgedt_m,dx=1/60) # dx ix x-spacing (1/60
    
    return base_yield_daily,pvgedt_yield_daily, base_yield_m, pvgedt_yield_m, m_yield, measured_irradiance


############################## Get output #####################################


def get_energy_yields (input_dates,pvgedt_loss_factor, plot_irrad):

    baseline_yields_day = []
    pvgedt_yields_day = []
    baseline_yields_m = []
    pvgedt_yields_m = []
    measured_yields = []
    
    for i in input_dates:
        baseline_yield_day,pvgedt_yield_day, baseline_yield_m, pvgedt_yield_m, measured_yield, measured_irradiance = calculate_energy_yield(i,pvgedt_loss_factor, plot_irrad)
        baseline_yields_day.append(float(baseline_yield_day))
        pvgedt_yields_day.append(float(pvgedt_yield_day))
        baseline_yields_m.append(float(baseline_yield_m))
        pvgedt_yields_m.append(float(pvgedt_yield_m))
        measured_yields.append(float(measured_yield))
        
         
    return baseline_yields_day,pvgedt_yields_day, baseline_yields_m, pvgedt_yields_m, measured_yields, measured_irradiance
    
############### for reference only ###############

# finding optimum "loss factor" when fitting to 13 Oct 2023
'''
pvgedt_loss_factor = 0.12

test_date_opt = ['2023-10-13']
plot_irrad = False

baseline_yields_daily, pvgedt_yields_daily, baseline_yields_comp, pvgedt_yields_comp, measured_yields, measured_irradiance = get_energy_yields(test_date_opt, pvgedt_loss_factor, plot_irrad)

print(measured_yields)
print(pvgedt_yields_comp)
'''

########################### MAIN CODE #########################

# define test date series
test_dates = ['2023-10-13',
              '2023-10-28',
              '2023-12-07',
              '2023-12-17',
              '2024-01-11',
              '2024-02-05']

# set desired loss factor (as a fraction between 0 and 1)
# must be zero for irradiance plots! - NEEDS FIX
pvgedt_loss_factor = 0

# Error Analysis: plot irradiance plots? Set True/False as desired

plot_irrad = True

# get power plots and energy yields for the series of test dates
baseline_yields_daily, topo_yields_daily, baseline_yields_comp, topo_yields_comp, measured_yields, measured_irradiance = get_energy_yields(test_dates, pvgedt_loss_factor, plot_irrad)

# organise data for output to csv file
output_data = pd.DataFrame({'Date': test_dates, 
                            'Daily_Baseline_Yield_Wh': baseline_yields_daily,
                            'Daily_Topo_Yield_Wh': topo_yields_daily,
                            'Measured_Yield_Wh': measured_yields,
                            'Baseline_Yield_Comparison_Wh': baseline_yields_comp,
                            'Topo_Yield_Comparison_Wh': topo_yields_comp})

output_data.to_csv('Energy_Yield_Outputs_bin.csv', index=False)
    
    
    