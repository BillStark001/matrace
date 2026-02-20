function [result1, result2, result3, result4, result5] = matrix_div_power(A, b, x, s)
    % A \ b  (mldivide: solve A*result = b)
    result1 = A \ b;
    % b' / A  (mrdivide: b transposed to row vector, then solve result*A = b')
    result2 = b' / A;
    % scalar ^ scalar (3rd power)
    result3 = s ^ 3;
    % matrix ^ integer
    result4 = A ^ 2;
    % element-wise power
    result5 = x .^ 2;
end
