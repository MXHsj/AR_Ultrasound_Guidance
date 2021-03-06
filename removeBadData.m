function data = removeBadData(data_raw)
% delete -1 values
data = data_raw;
bad_rows = [];
for row = 1:size(data,1)
    if ismember(-1,data(row,:))
        bad_rows = [bad_rows, row];
    end
end
data(bad_rows,:) = [];