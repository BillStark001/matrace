function [r1, r2, r3, r4] = string_ops(s1, s2)
    % r1: horizontal concatenation of char arrays
    r1 = [s1 ' ' s2];
    % r2: pass-through (char array)
    r2 = s1;
    % r3: string literal (double-quoted)
    r3 = "hello";
    % r4: char-array literal (single-quoted)
    r4 = 'world';
end
