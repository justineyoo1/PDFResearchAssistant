import datetime as dt
import io
import os

import pandas as pd
import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from gspread_pandas.conf import get_creds

from mdf_accruals.constants import GDRIVE_FOLDER_ID_MAP, REPORT_NAMES, STREAMLIT_FILE_TYPE, SVC_ACCT_NAME


class ReportReader:
    """
    ReportReader class.

    ReportReader class that defines the state and behavior of report_reader objects. Instantiated report_readers can
    then be used to store reports in memory once they have been uploaded by a user to the Streamlit app page, and return
    those reports to the calling routine as a list of Pandas DataFrames.
    """

    def __init__(self, webpage_columns: list[object]):
        """
        ReportReader constructor.

        Initialize a ReportReader object by setting the fields to the arguments passed to the constructor.

        Args:
        ----
            webpage_columns (list[object]): A list of Streamlit column objects passed from app.py. These columns are
                                            then used by the methods in the class to obtain the reports uploaded to the
                                            app by the user.

        """
        self.webpage_columns = webpage_columns

    def get_reports(self, submit_button: bool, mode: str = "PROD") -> dict:
        """
        Return a list of all reports uploaded by the user to the Streamlit page.

        Use private methods defined in the ReportReader class to create file_uploaders, read their associated reports
        into memory, then return copies of each report packaged into a dictionary to the calling routine.

        Args:
        ----
            submit_button (bool): True if the Streamlit form_submit_button was clicked on the app page.
            mode (str): Modes of operation for the app (determines folder used for read operations).
                        Defaults to "PROD".

        Returns:
        -------
            dict: A copy of all reports uploaded by the user to the Streamlit app page and
                  their associated names, packed into key-value pairs.

        """
        streamlit_uploaders = self.__get_file_uploaders(STREAMLIT_FILE_TYPE)

        if submit_button:
            uploaded_reports = self.__read_uploaded_reports(streamlit_uploaders)

            # return copies so the original report states remain unaltered
            reports_dict = {REPORT_NAMES[idx]: report.copy(deep=True) for idx, report in enumerate(uploaded_reports)}
            reports_dict[REPORT_NAMES[2]] = self.get_latest_gdrive_file(GDRIVE_FOLDER_ID_MAP[mode]["READ"], REPORT_NAMES[2])
            reports_dict[REPORT_NAMES[3]] = self.get_latest_gdrive_file(GDRIVE_FOLDER_ID_MAP[mode]["READ"], REPORT_NAMES[3])

            return reports_dict
        else:
            return None

    def __get_file_uploaders(self, file_type: str) -> list[object]:
        """
        Return file_uploaders for each Streamlit column.

        Use each column within the webpage_columns field to create a Streamlit file_uploader object for that column,
        then return a list of the file_uploaders to the calling routine.

        Args:
        ----
            file_type (str): The file extension type of the files that are used to create Streamlit file_uploader
                             objects.

        Returns:
        -------
            list[object]: A list of Streamlit file_uploader objects, where each column in the webpage_columns
                          field is assigned to a separate file_uploader.

        """
        activity_lifecycle_uploader = self.webpage_columns[0].file_uploader(
            label=f"Upload the most current version of the **{REPORT_NAMES[0]}** report:",
            type=[file_type],
        )
        payment_tracker_uploader = self.webpage_columns[-1].file_uploader(
            label=f"Upload the most current version of the **{REPORT_NAMES[1]}** report:",
            type=[file_type],
        )

        return [activity_lifecycle_uploader, payment_tracker_uploader]

    def __read_uploaded_reports(self, uploaders: list[object]) -> list[pd.DataFrame]:
        """
        Return a Pandas DataFrame for each Streamlit file_uploader.

        Use the Streamlit file_uploader object for each report uploaded by the user to read the report into memory,
        then return the reports to the calling routine in a list of Pandas DataFrames.

        Args:
        ----
            uploaders (list[object]): A list of Streamlit file_uploader objects, where each column in the webpage_columns
                                      field is assigned to a separate file_uploader.

        Returns:
        -------
            list[pd.DataFrame]: A list of all reports uploaded by the user to the Streamlit app page.

        """
        reports = []
        for idx, uploader in enumerate(uploaders):
            # error checking for reports not uploaded to the web app
            if uploader is None:
                st.warning(
                    f"A(n) {REPORT_NAMES[idx]} report must be provided, please review and try again.",
                    icon="⚠️",
                )
                st.stop()
            else:
                reports.append(pd.read_excel(uploader))

        return reports

    def __get_gdrive_metadata(self, folder_id: str) -> pd.DataFrame:
        """
        Return a dataframe of object metadata.

        Create a dataframe of metadata for each object contained within the Google Drive
        folder specified by the folder_id parameter, then return it to the caller.

        Args:
        ----
            folder_id (str): The ID of the GDrive folder containing the objects to obtain
                             metadata for.

        Returns:
        -------
            pandas.DataFrame: A dataframe of metadata for each object in the specified GDrive
                              folder.

        """
        creds = get_creds(SVC_ACCT_NAME, scope=["https://www.googleapis.com/auth/drive"])
        drive_service = build("drive", "v3", credentials=creds)

        # define query to specify the folder to list the contents of (do not show metadata for deleted objects)
        query = f"parents = '{folder_id}' and trashed=false"
        response = drive_service.files().list(supportsAllDrives=True, includeItemsFromAllDrives=True, q=query).execute()

        files = response.get("files")
        next_page_token = response.get("nextPageToken")

        # get metadata for all files in the folder with ID folder_id
        while next_page_token:
            response = drive_service.files().list(q=query).execute()
            files.extend(response.get("files"))
            next_page_token = response.get("nextPageToken")

        metadata = pd.DataFrame(files)

        return metadata

    def __get_report_date(self, name: str) -> dt.datetime.date:
        """
        Return a date string that has been cast to datetime.

        Parse the date component from the name string and cast it to a datetime.

        Args:
        ----
            name (str): A string containing the date for a given object.

        Returns:
        -------
            dt.datetime.date: The date component of the name parameter, cast to a datetime.

        """
        # parse the date from the name field based on the collector field
        date = name.split(".")[0].split("_")[-1]
        date = dt.datetime.strptime(date, "%m%d%Y")

        return date

    def get_latest_gdrive_file(self, folder_id: str, search_string: str) -> pd.DataFrame:
        """
        Return the name and ID of the most current file in a folder.

        Retrieve the file name and file ID of the most current file in the folder
        specified by the folder_id parameter, then return them to the caller.

        Args:
        ----
            folder_id (str): The ID of the folder containing the files whose most current
                             name and ID are to be returned.
            search_string (str): The string to search for in the file names to filter the
                                 files to be considered.

        Returns:
        -------
            list[str]: A list containing the name and ID of the most current file in the
                       folder whose ID is specified by the folder_id parameter.

        """
        # dataframe of metadata for all spreadsheet objects in folder with folder_id
        folder_metadata = self.__get_gdrive_metadata(folder_id)

        folder_metadata = folder_metadata[folder_metadata["mimeType"].str.contains("spreadsheet")]
        country_code_metadata = folder_metadata[folder_metadata["name"].str.contains(search_string)]

        # extract the date, then sort the sheets from oldest to newest
        country_code_metadata["date"] = country_code_metadata.apply(lambda x: self.__get_report_date(x["name"]), axis=1)
        country_code_metadata.sort_values(by="date", ascending=True, inplace=True)

        # grab the file name and file id of the newest spreadsheet in the folder
        current_file_name = country_code_metadata.iloc[-1]["name"]
        current_file_id = country_code_metadata.iloc[-1]["id"]

        return self.__get_gdrive_file(current_file_id, current_file_name)

    def __get_gdrive_file(self, file_id: str, file_name: str) -> pd.DataFrame:
        """
        Download a file from a Google Drive folder.

        Download a file with the file ID specified by the file_id parameter from a shared
        Google Drive folder.

        Args:
        ----
            file_id (str): The ID of the file to download.
            file_name (str): Name of the file in local file system after it is downloaded.

        Returns:
        -------
            pd.DataFrame: The contents of the file specified by the file_id and file_name
                          parameters.

        """
        # get user credentials
        creds = get_creds(SVC_ACCT_NAME, scope=["https://www.googleapis.com/auth/drive"])

        try:
            # create drive api client
            drive_service = build("drive", "v3", credentials=creds)

            request = drive_service.files().get_media(fileId=file_id)
            file = io.BytesIO()
            downloader = MediaIoBaseDownload(file, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                print(f"Download {int(status.progress() * 100)}.")

            file.seek(0)

            # opening file stream to write binary chunks
            with open(file_name, "wb") as file_stream:
                file_stream.write(file.read())
                file_stream.close()

        except HttpError as error:
            print(f"An error occurred: {error}")
            file = None

        gdrive_file = pd.read_excel(file_name)
        os.remove(file_name)

        return gdrive_file
