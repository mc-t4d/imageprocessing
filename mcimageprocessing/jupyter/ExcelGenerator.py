import openpyxl
from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation


def create_excel(self, datatype='EE', indicator=None):
    """
    :param self: The instance of the class.
    :return: Returns the created workbook.

    This method is used to create an Excel workbook with multiple sheets and set column headers for each sheet.
    The method takes no parameters.

    The structure of the workbook sheets and their properties are defined in the 'sheet_names' dictionary.
    Each sheet has a unique name and specifies the column names, column letters, and optionally,
    a resource ID and a list of options that will be used for data validation.

    The method uses the openpyxl library to create the workbook, add sheets, set column headers,
    and add data validation based on the 'Options' sheet.

    Finally, the method removes the default 'Sheet' created by openpyxl and returns the created workbook.
    """

    # Define the structure of the workbook sheets and their respective properties
    if datatype == 'EE':
        sheet_names = {'StartDate':
                           {'colnames': ['Indicator'],
                            'colletters': ['A'],
                            'resource_id': 'indicators'},
                       'EndDate':
                           {'colnames': ['Data_Element'],
                            'colletters': ['A'],
                            'resource_id': 'dataElements'},
                       'AdminLevel':
                           {'colnames': ['Admin', 'Frequency', 'Location', 'StartDate', 'EndDate'],
                            'colletters': ['A', 'B', 'C', 'D', 'E']},
                       'Value':
                           {'colnames': ['indicators', 'dataElements', 'Admin', 'Frequency'],
                            'colletters': ['A', 'B', 'C', 'D'],
                            'list_location': {'Indicators': sorted(
                                [x for x in self.resources_dictionary['indicators']['displayName'].unique()]),
                                'Data_Elements': sorted([x for x in
                                                         self.resources_dictionary['dataElements'][
                                                             'displayName'].unique()]),
                                'Admin': sorted(self.admin_levels),
                                'Frequency': ["Monthly", "Weekly", "Yearly"]
                            }
                            }
                       }

        wb = Workbook()

        # Create sheets and set column headers
        for x, y in sheet_names.items():
            wb.create_sheet(x)
            current = wb.get_sheet_by_name(x)
            if x != 'Options':
                for z, a in zip(y['colnames'], y['colletters']):
                    current[f"{a}1"] = z

        # Add options to the 'Options' sheet
        current = wb.get_sheet_by_name('Options')
        for z, a, values in zip(sheet_names['Options']['colnames'], sheet_names['Options']['colletters'],
                                sheet_names['Options']['list_location'].values()):
            for idx, option in enumerate(values, start=1):
                current[f"{a}{idx}"] = option
        else:
            pass

        settings = {}

        # Add data validation to each sheet based on the 'Options' sheet
        for x, y in sheet_names.items():
            current = wb.get_sheet_by_name(x)
            if x != 'Options':
                for colname, colletter, key, list in zip(sheet_names['Options']['colnames'],
                                                         sheet_names['Options']['colletters'],
                                                         sheet_names['Options']['list_location'].keys(),
                                                         sheet_names['Options']['list_location'].values()):
                    if x in ['Indicators', 'Data_Elements']:
                        if x == key:
                            current_dv = DataValidation(
                                type="list", formula1=f"Options!${colletter}$1:${colletter}${len(list)}",
                                showDropDown=False,
                                showInputMessage=True, errorStyle="stop", showErrorMessage=True, allowBlank=True
                            )
                            current.add_data_validation(current_dv)
                            for row in range(2, len(list)):
                                current_dv.add(current[f"A{row}"])
                    elif x in ['Settings']:
                        for n in y['colnames']:
                            if n == key:
                                settings[key] = {'colletter': colletter, 'list': list}

        # Add data validation to the 'Settings' sheet based on the 'Options' sheet
        current = wb.get_sheet_by_name('Settings')
        for x in sheet_names['Settings'].values():
            for y in x:
                for a, b in settings.items():
                    if y == a:
                        dv = DataValidation(
                            type="list", formula1=f"Options!${b['colletter']}$1:${b['colletter']}${len(b['list'])}",
                            showDropDown=False,
                            showInputMessage=True, errorStyle="stop", showErrorMessage=True, allowBlank=True
                        )


                        current.add_data_validation(dv)
                        testing = [(x, y) for x, y in
                                   zip(sheet_names['Settings']['colnames'], sheet_names['Settings']['colletters'])]
                        for num in testing:
                            if num[0] == y:
                                for row in range(2, len(b['list'])):
                                    dv.add(current[f"{num[1]}{row}"])

        # Remove the default 'Sheet' created by openpyxl
        del wb['Sheet']

        # Return the workbook
        return wb
