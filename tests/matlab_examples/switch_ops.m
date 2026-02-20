function [r1, r2, r3, r4] = switch_ops(x, s)
    % numeric switch with otherwise
    switch x
        case 1
            r1 = 10;
        case 2
            r1 = 20;
        otherwise
            r1 = 0;
    end

    % numeric switch without otherwise (no match -> falls through)
    r2 = 99;
    switch x
        case 99
            r2 = 1;
    end

    % string switch
    switch s
        case 'foo'
            r3 = 1;
        case 'bar'
            r3 = 2;
        otherwise
            r3 = 0;
    end

    % cell-case switch (multiple values per case)
    switch x
        case {1, 2}
            r4 = 100;
        case {3, 4}
            r4 = 200;
        otherwise
            r4 = 0;
    end
end
