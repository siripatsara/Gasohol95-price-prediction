import pandas as pd

# Read Excel file and examine structure
df = pd.read_excel('data/P06_current.xls', engine='xlrd')

print('Excel file structure analysis:')
print(f'Shape: {df.shape}')
print('\nFirst 20 rows:')

for i in range(min(20, len(df))):
    row_data = []
    for j in range(min(10, len(df.columns))):
        cell_val = df.iloc[i, j]
        if pd.notna(cell_val):
            row_data.append(str(cell_val)[:20])
        else:
            row_data.append('NaN')
    print(f'Row {i:2d}: {row_data}')

print('\nLooking for GASOHOL, E10, or DATE keywords:')
for i in range(min(50, len(df))):
    for j in range(len(df.columns)):
        cell_val = str(df.iloc[i, j]).upper()
        if any(keyword in cell_val for keyword in ['GASOHOL', 'E10', 'DATE', 'E20', 'ULG']):
            print(f'Found at Row {i}, Col {j}: {df.iloc[i, j]}')