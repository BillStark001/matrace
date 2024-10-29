function ret = basic()
    ret = 42;
end

function ret = array()
    ret = [1 2; 3 4];
end

function ret = cell()
    ret = {1 2; 3 4};
end

function ret = if_flow()
    a = 1;

    if a == 2
        ret = 1;
    else
        ret = 2;
    end

end

function ret = for_flow()
    ret = 0;

    for i = 1:5
        ret = ret + i;
    end

end

function ret = while_flow()
    ret = 114514;

    while ret < 1919810
        ret = ret + 114514;
    end

end
