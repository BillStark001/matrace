function dydt = ode_spring_mass(t, y, m, k)
    dydt = zeros(2, 1);
    dydt(1) = y(2);
    dydt(2) = -k / m * y(1);
end
