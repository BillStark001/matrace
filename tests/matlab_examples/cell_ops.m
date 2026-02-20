function [r1, r2, r3, r4, r5] = cell_ops()
    % simple 1x2 cell
    C = {10, 20};
    % linear indexing (1-based)
    r1 = C{1};
    r2 = C{2};

    % 2x2 cell, row-col indexing
    D = {1, 2; 3, 4};
    r3 = D{2, 1};

    % nested cell: {{42}}
    N = {{42}};
    r4 = N{1}{1};

    % cell with matrix elements; cell expansion into matrix
    E = {[1 2], [3 4]};
    r5 = [E{1}, E{2}];
end
