import os

import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from gspread_pandas.conf import get_creds

from mdf_accruals.constants import KEEP_COLUMNS_MAP, SVC_ACCT_NAME


class ReportWriter:
    """
    ReportWriter class.

    ReportWriter class to instantiate writer objects, which can then be used
    to get the write the final report to a specific location in the file system.
    """

    def __init__(self, report: pd.DataFrame, report_name: str):
        """
        ReportWriter constructor.

        Initialize a ReportWriter object by setting the fields to the arguments passed
        to the constructor.

        Args:
        ----
            report (pd.DataFrame): The contents of the final report.
            report_name (str): Name of the final report within the system file structure.

        """
        self.report = report
        self.report_name = report_name

    def write_report(
        self,
        sheet_name: str,
        formats: dict = None,
        currency_columns: list[str] = None,
        index: bool = False,
    ) -> str:
        """
        Write a tab to a workbook.

        Use a ReportWriter instantiated with the report_name class constant to write a formatted tab to an Excel
        workbook located at the path given by the report_name. Apply the formatting specified by the formats parameter
        to the appropriate columns.

        Args:
        ----
            sheet_name (str): The name of the sheet added to the workbook by the writer.
            formats (dict, optional): A dictionary specifying the format used when creating a Format object.
                                      Defaults to None.
            currency_columns (list[str], optional): The column names in which to apply the Currency format to.
                                                    Defaults to None.
            index (bool, optional): Whether or not to keep the current index column. Defaults to False.

        Returns:
        -------
            (str | PermissionError): The path in the local file system to the formatted and potentially
                                     compressed Excel file, where the file contains data from the report
                                     class field. If the file cannot be written to, return the PermissionError.

        """
        formatted_report = self.report.copy(deep=True)
        report_path = f"{self.report_name}.xlsx"
        header_columns = KEEP_COLUMNS_MAP["Accruals Report"][: len(KEEP_COLUMNS_MAP["Activity Lifecycle"]) - 2]

        # create a context manager and write the report to a tab of the file
        with pd.ExcelWriter(report_path, engine="xlsxwriter") as writer:
            try:
                formatted_report.to_excel(writer, sheet_name=sheet_name, index=index)
            except PermissionError as e:
                return e

            # widen columns and apply the proper formatting to the Accruals Report
            if formats is not None:
                workbook = writer.book

                currency_format = workbook.add_format(formats["Currency"])
                header_format = workbook.add_format(formats["Header"])

                for column in formatted_report:
                    column_length = max(formatted_report[column].astype(str).map(len).max(), len(column)) + 2
                    column_idx = formatted_report.columns.get_loc(column)

                    if column in currency_columns:
                        writer.sheets[sheet_name].set_column(column_idx, column_idx, column_length, currency_format)
                    else:
                        writer.sheets[sheet_name].set_column(column_idx, column_idx, column_length)

                for column_number, column_name in enumerate(formatted_report[header_columns].columns.values):
                    writer.sheets[sheet_name].write(0, column_number, column_name, header_format)

        return report_path

    def write_to_drive(self, folder_id: str, report_path: str) -> str:
        """
        Write to a drive.

        Write report to specified Google Drive folder.

        Args:
        ----
            folder_id (str): ID of the folder to upload a file to.
            report_path (str): Path of the report in local file system that is to be uploaded.

        Raises:
        ------
            PermissionError: If the calling routine does not have the necessary permissions to
                             write to the drive via the API.

        Returns:
        -------
            str: ID of the folder that the file was uploaded to.

        """
        try:
            creds = get_creds(SVC_ACCT_NAME, scope=["https://www.googleapis.com/auth/drive"])
            drive_service = build("drive", "v3", credentials=creds)

            parent_list = []
            parent_list.append(folder_id)

            file_metadata = {"name": report_path, "parents": parent_list}
            media = MediaFileUpload(report_path)
            drive_service.files().create(body=file_metadata, media_body=media, supportsAllDrives=True).execute()

            os.remove(report_path)
            return folder_id

        except PermissionError as e:
            raise PermissionError(f"An error occurred: {e}")
