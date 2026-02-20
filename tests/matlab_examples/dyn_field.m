function [r1, r2] = dyn_field(field_name, val)
    % dynamic field write
    s = struct('x', 0);
    s.(field_name) = val;
    % dynamic field read
    r1 = s.(field_name);
    % static read of the same field to cross-check
    r2 = s.x;
end
