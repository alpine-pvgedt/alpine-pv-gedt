# -*- coding: utf-8 -*-
"""
Created on Sun Aug 16 14:13:29 2026

@author: emily
"""
import matplotlib.pyplot as plt
import pandas as pd
import pvlib
import pytz


# import data classes and functions
from pvlib import clearsky
from datetime import datetime

# define PV module constants
surface_azimuth = 180 # due south
pv_module_area = 0.01169 # m^2
surface_tilt = 60
albedo = 0.796
efficiency = 0.22

### optional: plot example plot of baseline and PV-GEDT power for sites in the spatial sensitivity study

def get_power_sensitivity(site_latitude,site_longitude,site_altitude,topo_sunrise,topo_sunset):
    
    times = pd.date_range(start='2023-12-17', end='2023-12-18', freq='1Min', tz='Europe/Zurich')
    site_solpos = pvlib.solarposition.get_solarposition(times, site_latitude, site_longitude, site_altitude)
    site_apparent_zenith = site_solpos['apparent_zenith']

    site_airmass = pvlib.atmosphere.get_relative_airmass(site_apparent_zenith)
    site_pressure = pvlib.atmosphere.alt2pres(site_altitude)
    site_airmass = pvlib.atmosphere.get_absolute_airmass(site_airmass, site_pressure)

    site_linke_turbidity = pvlib.clearsky.lookup_linke_turbidity(times, site_latitude, site_longitude)

    # get irradiance dataframe using ineichen & perez model from pvlib
    site_dni_extra = pvlib.irradiance.get_extra_radiation(times)
    site_ineichen = clearsky.ineichen(site_apparent_zenith, site_airmass, site_linke_turbidity, site_altitude, site_dni_extra)
    
    # get components of solar position
    site_solar_zenith = site_solpos['zenith']
    site_solar_azimuth = site_solpos['azimuth']

    # get irradiance components
    site_dni = site_ineichen['dni']
    site_ghi = site_ineichen['ghi']
    site_dhi = site_ineichen['dhi']

    # get plane-of-array (POA) irradiance using pvlib
    site_poa_irradiance = pvlib.irradiance.get_total_irradiance(surface_tilt, surface_azimuth, site_solar_zenith, site_solar_azimuth, site_dni, site_ghi, site_dhi, dni_extra=None, airmass=None, albedo=albedo, surface_type=None, model='klucher', model_perez='allsitescomposite1990')
    
    # get baseline POA irradiance (not modified with topo sunrise/sunset times)
    site_poa_baseline = site_poa_irradiance['poa_global']

    # get PV-GEDT POA irradiance by modifying baseline using topo sunrise and sunset times
    site_poa_pvgedt = site_poa_baseline.copy()
    
    topo_sunrise = pytz.timezone('Europe/Zurich').localize(topo_sunrise)
    topo_sunset = pytz.timezone('Europe/Zurich').localize(topo_sunset)
    

    for i in site_poa_pvgedt.index:
        if i < topo_sunrise:
            site_poa_pvgedt.loc[i] = 0              
        elif i > topo_sunset:
            site_poa_pvgedt.loc[i] = 0
            
    # convert POA irradiances into W (using the module cell area)
    site_poa_baseline = site_poa_baseline.mul(pv_module_area)
    site_poa_pvgedt = site_poa_pvgedt.mul(pv_module_area)
    
    # get power output
    site_power_baseline = site_poa_baseline.mul(efficiency)
    site_power_pvgedt = site_poa_pvgedt.mul(efficiency)
    
    return site_power_baseline, site_power_pvgedt

    
latitude_E = 46.8362
longitude_E = 9.813
altitude_E = 2442
E_topo_sunrise = datetime(2023,12,17,8,16,0)
E_topo_sunset = datetime(2023,12,17,13,57,0)
E_power_baseline, E_power_pvgedt = get_power_sensitivity(latitude_E, longitude_E, altitude_E, E_topo_sunrise,E_topo_sunset)


latitude_H = 46.83928
longitude_H = 9.81114
altitude_H = 2526
H_topo_sunrise = datetime(2023,12,17,8,15,0)
H_topo_sunset = datetime(2023,12,17,15,39,0)
H_power_baseline, H_power_pvgedt = get_power_sensitivity(latitude_H, longitude_H, altitude_H, H_topo_sunrise, H_topo_sunset)

fig,ax = plt.subplots()
E_power_baseline.plot(ax = ax, color = 'darkviolet', linestyle = 'dashed', label = 'Baseline: Site E', linewidth = 2.5)
E_power_pvgedt.plot(ax = ax, color = 'turquoise', label = 'PV-GEDT: Site E', linewidth = 2.5)

H_power_baseline.plot(ax = ax, color = 'fuchsia', linestyle = 'dashed', label = 'Baseline: Site H', linewidth = 2.5)
H_power_pvgedt.plot(ax = ax, color = 'dimgray', label = 'PV-GEDT: Site H', linewidth = 2.5)

ax.set_xlabel('Timestamp (hh:mm)', fontsize = 15)
ax.set_ylabel('Power Output (W)', fontsize = 15)
ax.set_ybound(upper=4.2)
ax.tick_params(axis='y', which='major', labelsize=12)
ax.tick_params(axis='x', which='major', labelsize=12)
ax.tick_params(axis='x', which='minor', labelsize=12)
ax.legend(loc=2, prop ={'size':11});
