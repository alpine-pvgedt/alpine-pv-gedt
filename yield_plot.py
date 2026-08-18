# -*- coding: utf-8 -*-
"""
Created on Sun Aug 16 16:17:12 2026

@author: emily
"""

# import packages
import matplotlib.pyplot as plt
import pandas as pd
from scipy import stats

# import calculated yield data for series of test dates
yield_data = pd.read_csv('daily-yield-data.csv')
yield_data = yield_data.sort_values(by=['Baseline_Yield_Wh'])

################## plot baseline yield against PV-GEDT yield  ####################
fig,ax = plt.subplots()

yield_data.plot.scatter(x = 'Baseline_Yield_Wh', y = 'PVGEDT_Yield_Wh', ax=ax, c='darkorchid', s=50, label = 'No loss factor')
yield_data.plot.scatter(x = 'Baseline_Yield_Wh', y = 'LF_PVGEDT_Yield_Wh', ax=ax, c='darkorange', s=50, label = '12% loss factor')
ax.set_xlabel('Baseline Energy Yield (Wh)', fontsize = 15)
ax.set_ylabel('PVGEDT Energy Yield (Wh)', fontsize = 15)
ax.tick_params(axis='y', which='major', labelsize=15)
ax.tick_params(axis='x', which='major', labelsize=15)
ax.tick_params(axis='x', which='minor', labelsize=15)

#### plot line of best fit and get statistics ####

x_baseline_yield = yield_data['Baseline_Yield_Wh']
y_pvgedt_yield_nom = yield_data['PVGEDT_Yield_Wh']
y_pvgedt_yield_loss = yield_data['LF_PVGEDT_Yield_Wh']

def get_statistics(base_yield,pvgedt_yield,colour):

    # inspired from https://www.w3schools.com/python/python_ml_linear_regression.asp
    slope, intercept, r, p, std_err = stats.linregress(base_yield, pvgedt_yield)
    ax.plot(base_yield, ((slope*base_yield)+intercept), c=colour, linestyle = 'dashed')
    ax.set_xbound(lower=12, upper=22)
    ax.set_ybound(lower=12,upper=22)
    slope = round(slope,3)
    intercept = round(intercept,3)

    
    ##### get R^2 value and display on graph ####
    r2 = round(r**2,4)

    return slope,intercept,r2

slope_n , intercept_n, r2_n = get_statistics(x_baseline_yield,y_pvgedt_yield_nom,'darkorchid')
ax.text(17.6, 21.1, 'y = ' + str(slope_n) + 'x' + str(intercept_n), c='darkorchid', size=14, weight = 'semibold')
ax.text(17.6, 20.3, 'R\u00b2 = ' + str(r2_n), c= 'darkorchid', size = 14, weight = 'semibold')

slope_loss, intercept_loss, r2_loss = get_statistics(x_baseline_yield,y_pvgedt_yield_loss,'darkorange')
ax.text(12.6, 13.4, 'y = ' + str(slope_loss) + 'x' + str(intercept_loss), c = 'darkorange', size=14, weight = 'semibold')
ax.text(12.6, 12.6, 'R\u00b2 = ' + str(r2_loss), c='darkorange',size = 14, weight = 'semibold')

ax.legend(loc=2, prop ={'size':12});

