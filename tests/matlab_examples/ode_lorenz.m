function dydt = ode_lorenz(t, y, sigma, rho, beta)
    % sigma = 10;
    % rho = 28;
    % beta = 8/3;
    dydt = zeros(3, 1);
    dydt(1) = sigma * (y(2) - y(1));
    dydt(2) = y(1) * (rho - y(3)) - y(2);
    dydt(3) = y(1) * y(2) - beta * y(3);
end
