function [U] = solve_heat_equation(nx, nt, dx, dt, alpha)
    U = zeros(nx, nt);
    U(:, 1) = sin(pi * (0:nx - 1) / (nx - 1)); % init cond
    r = alpha * dt / dx ^ 2;

    for j = 1:nt - 1

        for i = 2:nx - 1
            U(i, j + 1) = U(i, j) + r * (U(i + 1, j) - 2 * U(i, j) + U(i - 1, j));
        end

        U(1, j + 1) = 0; % bound
        U(nx, j + 1) = 0; % bound
    end

end
