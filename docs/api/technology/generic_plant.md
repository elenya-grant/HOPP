(tech:generic)=
# Generic Plant

Generic plant generator model can be used to represent either a [single generator system](tech:generic-single) or [multiple generator systems](tech:generic-multi).

```{note}
There is no cost model integrated with this generation class.
```

## Generic Plant Configuration

```{eval-rst}
.. autoclass:: hopp.simulation.technologies.generic.generic_plant.GenericConfig
    :members:
    :exclude-members: _get_model_dict, as_dict, get_model_defaults, logger
    :member-order: bysource
```

### Generic plant configuration for GenericSystem
To represent a [single generator system](tech:generic-single), the technology input file is formatted as follows:
```yaml
generic:
    system_capacity_kw:
    system_capacity_kwac:
    generation_profile_kw:
```

### Generic plant configuration for GenericMultiSystem
To represent [multiple generic systems](tech:generic-multi), the technology input file is formatted as follows:
```yaml
generic:
    system1:
        system_capacity_kw:
        system_capacity_kwac:
        generation_profile_kw:
        subsystem_name: system1
    system2:
        system_capacity_kw:
        system_capacity_kwac:
        generation_profile_kw:
        subsystem_name: system2
```

(tech:generic-single)=
## Generic System

```{eval-rst}
.. autoclass:: hopp.simulation.technologies.generic.generic_plant.GenericSystem
    :members:
    :exclude-members: hopp.simulation.technologies.power_source.PowerSource, hopp.simulation.base.BaseClass, PowerSource, calc_gen_max_feasible_kwh, calc_capacity_credit_percent, calc_nominal_capacity, calculate_total_installed_cost, copy, export, initialize_financial_values, plot, set_overnight_capital_cost, import_financial_model, setup_performance_model, simulate, simulate_financials, simulate_power, value, om_variable, logger, generation_profile, gen_max_feasible, from_dict, federal_taxes, assign, as_dict, _get_model_dict, annual_energy_kwh, benefit_cost_ratio, capacity_credit_percent, capacity_payment, capacity_price, construction_financing_cost, cost_installed, debt_payment, degradation, dispatch, dispatch_factors, energy_purchases, energy_sales, energy_value, federal_depreciation_total, get_model_defaults, insurance_expense, internal_rate_of_return, levelized_cost_of_energy_nominal, levelized_cost_of_energy_real, net_present_value, om_capacity, om_capacity_expense, om_fixed, om_fixed_expense, om_production, om_total_expense, om_variable_expense, ppa_price, tax_incentives, total_installed_cost, total_revenue
```

(tech:generic-multi)=
## Generic Multi-plant
```{eval-rst}
.. autoclass:: hopp.simulation.technologies.generic.generic_multi.GenericMultiSystem
    :members:
    :exclude-members: hopp.simulation.technologies.power_source.PowerSource, hopp.simulation.base.BaseClass, PowerSource, calc_gen_max_feasible_kwh, calc_capacity_credit_percent, calc_nominal_capacity, calculate_total_installed_cost, copy, export, initialize_financial_values, plot, set_overnight_capital_cost, import_financial_model, setup_performance_model, simulate, simulate_financials, simulate_power, value, om_variable, logger, generation_profile, gen_max_feasible, from_dict, federal_taxes, assign, as_dict, _get_model_dict, annual_energy_kwh, benefit_cost_ratio, capacity_credit_percent, capacity_payment, capacity_price, construction_financing_cost, cost_installed, debt_payment, degradation, dispatch, dispatch_factors, energy_purchases, energy_sales, energy_value, federal_depreciation_total, get_model_defaults, insurance_expense, internal_rate_of_return, levelized_cost_of_energy_nominal, levelized_cost_of_energy_real, net_present_value, om_capacity, om_capacity_expense, om_fixed, om_fixed_expense, om_production, om_total_expense, om_variable_expense, ppa_price, tax_incentives, total_installed_cost, total_revenue
    :member-order: bysource
```