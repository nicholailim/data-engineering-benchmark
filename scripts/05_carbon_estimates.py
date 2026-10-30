"""
05_carbon_estimates.py
Reproduces the indicative carbon comparison (Sections 3.4 and 4.8, Table 9):
  * local laptop electricity and emissions,
  * cloud emissions under three emission factors,
  * a bottom-up check of the assumed cloud electricity use with the
    Cloud Carbon Footprint (CCF) method.

IMPORTANT: the cloud electricity use of about 346 kWh per year is a conservative
planning ASSUMPTION (roughly one third of local use), not a measured value.
Emission factors are cited in the paper: Philippines 0.691 kg CO2e/kWh (ref. 20),
Singapore grid 0.402 kg CO2e/kWh, 2024 (ref. 22), Google Cloud Singapore region
grid intensity 367 g CO2e/kWh (ref. 23).  CCF coefficients (ref. 24): Google Cloud
1.34 W min and 4.98 W max per vCPU, 0.392 W per GB memory, PUE 1.10.

Run from the repository root:
    python scripts/05_carbon_estimates.py
"""
import os
import pandas as pd

# ---------------------------- local environment ---------------------------------
LAPTOPS, WATTS, HOURS_PER_DAY, DAYS = 8, 45, 8, 30
local_kwh = LAPTOPS * WATTS / 1000 * HOURS_PER_DAY * DAYS * 12          # 1,036.8 kWh/year
CLOUD_KWH_ASSUMED = 346                                                  # planning assumption

# ---------------------------- emission factors (kg CO2e per kWh) -----------------
F_PH, F_SG, F_GOOGLE = 0.691, 0.402, 0.367

local_kg = local_kwh * F_PH
rows = [('Local laptops (Philippines)', local_kwh, F_PH, local_kg, None)]
for label, f in [('Cloud (assumed), Philippine factor (conservative bound)', F_PH),
                 ('Cloud (assumed), Singapore grid factor', F_SG),
                 ('Cloud (assumed), Google regional grid intensity', F_GOOGLE)]:
    kg = CLOUD_KWH_ASSUMED * f
    rows.append((label, CLOUD_KWH_ASSUMED, f, kg, 1 - kg / local_kg))
table9 = pd.DataFrame(rows, columns=['Scenario', 'Electricity (kWh/year)', 'Factor (kg CO2e/kWh)',
                                     'Emissions (kg CO2e/year)', 'Reduction vs laptops'])
table9['Electricity (kWh/year)'] = table9['Electricity (kWh/year)'].round(0).astype(int)
table9['Emissions (kg CO2e/year)'] = table9['Emissions (kg CO2e/year)'].round(0).astype(int)
table9['Reduction vs laptops'] = table9['Reduction vs laptops'].map(lambda x: '-' if pd.isna(x) else f'{x:.0%}')
print('Table 9 - indicative annual operational emissions\n', table9.to_string(index=False))

print(f'\nLocal electricity: {local_kwh:,.1f} kWh/year; assumed cloud use is {CLOUD_KWH_ASSUMED / local_kwh:.0%} of it.')
print(f'Cloud electricity would have to be about {local_kg / F_SG / CLOUD_KWH_ASSUMED:.1f} times the assumed value '
      f'(about {local_kg / F_SG:,.0f} kWh/year) before cloud emissions match the laptops at the Singapore factor.')

# ---------------------------- bottom-up check (CCF method) -----------------------
JOBS_PER_MONTH, HOURS_PER_JOB, VCPU, MEM_GB = 300, 0.5, 4, 15              # model assumptions
vcpu_hours = JOBS_PER_MONTH * HOURS_PER_JOB * VCPU                          # 600 per month
gb_hours = JOBS_PER_MONTH * HOURS_PER_JOB * MEM_GB                          # 2,250 per month
W_MIN, W_MAX, W_MEM, PUE = 1.34, 4.98, 0.392, 1.10

def cloud_kwh_per_year(util):
    watts_per_vcpu = W_MIN + util * (W_MAX - W_MIN)
    monthly_kwh = (vcpu_hours * watts_per_vcpu + gb_hours * W_MEM) / 1000 * PUE
    return monthly_kwh * 12

central, low, high = cloud_kwh_per_year(0.5), cloud_kwh_per_year(0.0), cloud_kwh_per_year(1.0)
print(f'\nBottom-up Dataflow electricity: {central:.0f} kWh/year at 50% utilisation '
      f'({low:.0f}-{high:.0f} kWh/year for 0-100%).')
print(f'The planning assumption is {CLOUD_KWH_ASSUMED / central:.0f} times the central estimate.')
for label, f in [('Philippine factor', F_PH), ('Singapore factor', F_SG)]:
    kg = central * f
    print(f'  {label}: {kg:.0f} kg CO2e/year -> reduction {1 - kg / local_kg:.1%}')

os.makedirs('outputs', exist_ok=True)
table9.to_csv('outputs/table9_emissions.csv', index=False)
print('\nSaved outputs/table9_emissions.csv')
