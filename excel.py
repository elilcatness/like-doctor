from csv import reader, writer
from openpyxl import Workbook


def make_csv_rows_unique(input_filename, output_filename, delimiter=';'):
    links = []
    rows = []
    with open(input_filename, encoding='utf-8') as f:
        for row in reader(f, delimiter=delimiter):
            if row[-1] not in links:
                links.append(row[-1])
                rows.append(row)
    with open(output_filename, 'w', newline='', encoding='utf-8') as f:
        csv_writer = writer(f, delimiter=delimiter)
        csv_writer.writerows(rows)


def from_csv_to_xlsx(csv_filename, xlsx_filename=None, delimiter=';'):
    xlsx_filename = (xlsx_filename if xlsx_filename and isinstance(xlsx_filename, str)
                     else f'{".".join(csv_filename.split(".")[:-1])}.xlsx')
    workbook = Workbook()
    sheet = workbook.active
    with open(csv_filename, encoding='utf-8') as f:
        for i, row in enumerate(reader(f, delimiter=delimiter)):
            for j, cell in enumerate(row):
                sheet.cell(i + 1, j + 1, cell)
    workbook.save(xlsx_filename)
    print('OK')


if __name__ == '__main__':
    make_csv_rows_unique('output.csv', 'results/output.csv')
    from_csv_to_xlsx('results/output.csv')
