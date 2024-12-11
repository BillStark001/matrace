function [result1, result2, result3, result4] = matrix_operations(A, B)
    result1 = A * B;
    result2 = A';
    result3 = B(2, 1);
    result4 = [
        1;
        2;
        3;
        4;
    ];
end
