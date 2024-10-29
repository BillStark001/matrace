function dydt = ode_msd_system(t, y, m, c, k)
    x = y(1);
    v = y(2);
    
    dxdt = v;
    dvdt = (-c * v - k * x) / m;
    
    dydt = [dxdt; dvdt];
  end