import datetime
import calendar
import sys

from dateutil.relativedelta import relativedelta
from sortedcontainers import SortedDict


def main(file_path):
    old_report = read_file(file_path)
    result_txt = "converted_payroll_export.txt"
    clean_file(result_txt)
    convert_report(old_report, result_txt)


def read_file(file_path: str) -> list:
    #"C:\\Users\kateryna.bala\Downloads\AttendoChanges10.txt"
    with open(file_path) as f:
        lines = f.readlines()
        return lines


def clean_file(file):
    # clean txt file or create new file if file not exist
    open(file, "w").close()


def convert_report(old_report, result_txt):
    actual_index = ""
    old_report_rows = SortedDict()
    i = 0
    end_index = 0

    rows_count = len(old_report)
    for row in old_report:
        end_index = end_index + 1
        key = ""
        if row[0] == "B":
            # key for B row = '01_' + TRANSNR
            key = "01_" + row[94:96]
        else:
            # key for A row = '02_' + LONEART + STARTDATUM + TRANSNR
            key = "02_" + row[27:30] + row[96:102] + row[94:96] + "_" + string_format_with_len(str(end_index), len(str(rows_count)))

        index = row[1:17]
        if index != actual_index:

            convert_rows_and_write_results(old_report_rows, result_txt)
            old_report_rows = SortedDict()
            actual_index = index
            old_report_rows[key] = row
        else:
            old_report_rows[key] = row

    convert_rows_and_write_results(old_report_rows, result_txt)


def convert_rows_and_write_results(old_report_rows, result_txt):
    new_report_rows = SortedDict()
    for key in old_report_rows:
        row = old_report_rows[key]
        if row[0] == "B":
            new_report_rows = convert_b_row(key, row, new_report_rows)
        elif row[0] == "A":
            if row[287:299] == " " * 12:
                new_report_rows = convert_a_row_with_empty_datum(key, row, new_report_rows)
            elif row[289:291] == row[295:297]:
                new_report_rows = convert_a_row_with_datum_in_the_same_month(key, row, new_report_rows)
            elif row[289:291] != row[295:297]:
                new_report_rows = convert_a_row_with_datum_in_different_months(key, row, new_report_rows)
            else:
                new_report_rows[key] = "INCORRECT ROW: row[0] is 'A' but if rules not exist for row '" + row + "' "
        else:
            new_report_rows[key] = "INCORRECT ROW: row[0] is NOT 'A' or 'B'"

    write_results(result_txt, new_report_rows)


def convert_b_row(key, row, new_report_rows):
    new_row = row
    # add "0"*18 at the end of row
    new_row = new_row[0:len(row) - 1] + "0" * 18 + new_row[len(row) - 1:len(row)]
    # if TRANSNR = "01" or "02"
    if new_row[94:96] == "01" or new_row[94:96] == "02":
        # SEMUTFAKT = "0"*5
        new_row = new_row[0:247] + "0" * 5 + new_row[252:len(new_row)]
    if new_row[94:96] == "03":
        # add PERIODLANGD
        new_row = new_row[0:102] + str(daysInMonth(int(new_row[96:98]), int(new_row[98:100]))) + new_row[
                                                                                                 104:len(new_row)]
    new_report_rows[key] = new_row
    # if TRANSNR = "03", create new row
    if new_row[94:96] == "03":
        key = "01_04"
        # new STARTDATUM = STARTDATUM from row with TRANSNR = "03" + 1 month
        datum_plus_month = datetime.date(int(row[96:98]), int(row[98:100]), 1) + relativedelta(months=+1)
        # TRANSNR = "04"
        new_row = new_row[0:94] + "04" + datum_in_right_format(datum_plus_month) + new_row[102: len(new_row)]
        # add PERIODLANGD
        new_row = new_row[0:102] + str(daysInMonth(int(new_row[96:98]), int(new_row[98:100]))) + new_row[
                                                                                                 104:len(new_row)]
        new_report_rows[key] = new_row

    return new_report_rows


def convert_a_row_with_empty_datum(key, row, new_report_rows):
    new_from_day = 0
    new_to_day = 0
    position = -1

    for i in range(0, 35):
        if row[104 + i * 4: 108 + i * 4] != "0000":
            new_to_day = i + 1
            position = i
            if new_from_day == 0:
                new_from_day = i + 1

    new_row = row
    # AVVIKDAGAR = "0"*140
    new_row = new_row[0:104] + "0" * 140 + new_row[244: len(new_row)]
    # SEMUTFAKT = "0"*5
    new_row = new_row[0:248] + "0" * 5 + new_row[253: len(new_row)]
    # TRANSNR = 01
    new_row = new_row[0:94] + "01" + new_row[96:len(new_row)]
    # PERIODLANGD = 00
    new_row = new_row[0:102] + "00" + new_row[104:len(new_row)]

    new_from = row[96:100] + string_format_with_len(new_from_day, 2)
    new_to = row[96:100] + string_format_with_len(new_to_day, 2)
    # STARTDATUM = from_new
    new_row = new_row[0:96] + new_from + new_row[102:len(new_row)]
    # FROMDATUMCB = new_from
    new_row = new_row[0:287] + new_from + new_row[293:len(new_row)]
    # TOMDATUMCB = new_to
    new_row = new_row[0:293] + new_to + new_row[299:len(new_row)]
    if new_from_day == new_to_day:
        row_b_01 = new_report_rows['01_01']
        row_b_02 = new_report_rows['01_02']
        if row_b_01[98:100] == new_row[98:100]:
            b_row = row_b_01
        elif row_b_02[98:100] == new_row[98:100]:
            b_row = row_b_02
        else:
            new_row = "INCORRECT ROW: new_row[98:100] is NOT row_b_01[98:100] or row_b_02[98:100]"

        # LONEART, where AVVIKDAGAR will be moved to ANTAL
        list_of_exceptions_loneart = ["136", "135"]

        if list_of_exceptions_loneart.__contains__(new_row[27:30]):
            new_antal = string_format_with_len(row[104 + position * 4: 108 + position * 4], 6)
            new_row = new_row[0:253] + new_antal + new_row[259: len(new_row)]
            # STARTDATUM = from_new
            new_row = new_row[0:96] + row[96:102] + new_row[102:len(new_row)]
        else:
            a_value = float(row[104 + position * 4: 108 + position * 4]) / 100
            b_value = float(b_row[104 + position * 4: 108 + position * 4]) / 100

            # a_value and b_value in minutes
            a_value = int(a_value * 60)
            b_value = int(b_value * 60)
            # save 4 chars after "0."
            value = string_format_with_len(str(a_value / b_value)[2:6], 7)
            # write value as OMF
            new_row = new_row[0:299] + value + new_row[306: len(new_row)]

    new_report_rows[key] = new_row
    return new_report_rows


def convert_a_row_with_datum_in_the_same_month(key, row, new_report_rows):
    # create new row with:
    new_row = row
    # TRANSNR = "01"
    new_row = new_row[0:94] + "01" + new_row[96:len(new_row)]
    # STARTDATUM = from_new
    #new_row = new_row[0:96] + row[287:293] + new_row[102:len(new_row)]
    # PERIODLANGD = "00"
    new_row = new_row[0:102] + "00" + new_row[104:len(new_row)]
    # SEMUTFAKT = "0"*5
    new_row = new_row[0:248] + "0" * 5 + new_row[253: len(new_row)]

    new_report_rows[key] = new_row
    return new_report_rows


def convert_a_row_with_datum_in_different_months(key, row, new_report_rows):
    from_datum = datetime.date(int(row[287:289]), int(row[289:291]), int(row[291:293]))
    to_datum = datetime.date(int(row[293:295]), int(row[295:297]), int(row[297:299]))
    # calculate month count between FROMDATUM and TOMDATUM
    month_count = (to_datum.year - from_datum.year) * 12 + to_datum.month - from_datum.month + 1
    # for every month create new row
    for i in range(0, month_count):
        # FROMDATUM and TOMDATUM for new row
        if i == 0:
            from_new = datum_in_right_format(from_datum)
            last_day_in_month = daysInMonth(int(from_datum.year), int(from_datum.month))
            to_new = datum_in_right_format(datetime.date(int(row[287:289]), int(row[289:291]), last_day_in_month))
        elif i == (month_count - 1):
            from_new = datum_in_right_format(datetime.date(int(row[293:295]), int(row[295:297]), 1))
            to_new = datum_in_right_format(to_datum)
        else:
            datum_plus_month = datetime.date(int(row[287:289]), int(row[289:291]), 1) + relativedelta(months=+i)
            from_new = datum_in_right_format(datum_plus_month)
            last_day_in_month = daysInMonth(int(datum_plus_month.year), int(datum_plus_month.month))
            to_new = datum_in_right_format(
                datetime.date(datum_plus_month.year, datum_plus_month.month, last_day_in_month))
        # create new row with:
        new_row = row
        # TRANSNR = "01"
        new_row = new_row[0:94] + "01" + new_row[96:len(new_row)]
        # STARTDATUM = from_new
        new_row = new_row[0:96] + from_new + new_row[102:len(new_row)]
        # PERIODLANGD = "00"
        new_row = new_row[0:102] + "00" + new_row[104:len(new_row)]
        # SEMUTFAKT = "0"*5
        new_row = new_row[0:248] + "0" * 5 + new_row[253: len(new_row)]
        # FROMDATUM  = from_new
        new_row = new_row[0:287] + from_new + new_row[293:len(new_row)]
        # TOMDATUM = to_new
        new_row = new_row[0:293] + to_new + new_row[299:len(new_row)]
        # OMF = "0"*7
        new_row[0:299] + "0" * 7 + new_row[306: len(new_row)]

        new_report_rows[key] = new_row
        return new_report_rows


def daysInMonth(input_year, input_month):
    # calculate days in month
    return calendar.monthrange(input_year, input_month)[1]


def datum_in_right_format (datum):
    # write datum as string in format YYMMDD
    return string_format_with_len(datum.year, 2)+string_format_with_len(datum.month, 2) + string_format_with_len(datum.day, 2)


def string_format_with_len (input, new_len):
    input = str(input)
    str_part = ""
    for i in range(0, new_len - len(input)):
        str_part = str_part + "0"
    output = str_part + input
    return output


def write_results(file, rows):
    # add new row to file
    with open(file, 'a') as f:
        for key in rows:
            f.writelines(rows[key])


if __name__ == "__main__":
    # read file name from cmd
    # cmd request python convert_payroll_export.py AttendoChanges10.txt
    file_path: str = sys.argv[1]
    main(file_path)