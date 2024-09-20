function [result1, result2, result3] = element_wise_operations(A, B)
    result1 = A .* B;
    result2 = A > B;
    result3 = sum(A(:));
end
