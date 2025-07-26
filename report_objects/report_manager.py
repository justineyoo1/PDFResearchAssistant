import datetime as dt

import pandas as pd

from mdf_accruals.constants import (
    ACCRUAL_MONTHS,
    COLUMN_RENAME_MAP,
    IMPUTED_VALUES_MAP,
    KEEP_COLUMNS_MAP,
    REPORT_NAMES,
    STANDARD_ERROR_MESSAGES,
)
from mdf_accruals.report_objects.errors.column_subset_error import ColumnSubsetError
from mdf_accruals.report_objects.errors.join_key_error import JoinKeyError


class ReportManager:
    """
    ReportManager class.

    ReportManager class to instantiate manager objects. These can then be used to mutate and clean columns
    within pandas DataFrames that are used by the program.
    """

    def __init__(
        self,
        reports: dict,
    ):
        """
        ReportManager constructor.

        Initialize a ReportManager object by setting the fields to the arguments passed to the constructor.

        Args:
        ----
            reports (dict): A copy of all reports uploaded by the user to the Streamlit app page and their
                            associated names, packed into key-value pairs.

        """
        self.reports = reports

    def get_raw_reports(self) -> dict:
        """
        Get the raw reports.

        Return the unaltered reports that were uploaded by the user to the Streamlit app page and read from
        the shared GDrive.

        Returns
        -------
            dict: A dictionary of all unaltered reports uploaded by the user to the Streamlit app page and
                  their associated names, packed into key-value pairs.

        """
        return self.reports

    def prepare_reports(self) -> dict:
        """
        Proprocess all reports.

        Preprocess each report in the reports field by calling the corresponding private helper method.
        Store the preprocessed reports in a new dictionary, then return the dictionary to the calling
        subroutine.

        Returns
        -------
            dict: A copy of all reports uploaded by the user to the Streamlit app, where each report
                  has been preprocessed and stored in a new dictionary.

        """
        helper_methods = [
            self.__prepare_activity_lifecycle,
            self.__prepare_gbd_tracker,
            self.__prepare_country_codes,
            self.__prepare_activities_table,
        ]
        # call the appropriate preprocessing method for each report in the reports field
        prepared_reports = {REPORT_NAMES[idx]: method() for idx, method in enumerate(helper_methods)}

        return prepared_reports

    def get_pa_to_claim_factors(self) -> pd.DataFrame:
        """
        Return PA to Claims Factor columns from Activities Table.

        Create a copy of the Activities Table within the reports fields, subset it to include only the
        "Activity", "APAC", "EMEA", "LATAM", and "NA columns, then return the table to the calling
        subroutine.

        Returns
        -------
            pd.DataFrame: A copy of ther Activities Table, where the report has been subset by select
                          columns.

        """
        activities_table = self.reports[REPORT_NAMES[3]].copy(deep=True)
        try:
            pa_to_claim_factors = activities_table[KEEP_COLUMNS_MAP["Activities Table"]]
        except KeyError:
            raise ColumnSubsetError(STANDARD_ERROR_MESSAGES["ColumnSubsetError"])

        return pa_to_claim_factors

    def __prepare_activity_lifecycle(self) -> pd.DataFrame:
        """
        Prepare the Activity Lifecycle report.

        Use a ReportManager instantiated in main to turn a Excel sheet into a DataFrame.

        Returns
        -------
            pd.DataFrame: A copy of the Activity Lifecycle Report, where the report has been filtered by PA Status. Two
                          column headers renamed according to COLUMN_RENAME_MAP constant, and a new Claim Approved in Local
                          Currency column created.

        """
        activity_lifecycle = self.reports[REPORT_NAMES[0]].copy(deep=True)
        # rename / subset columns, fill missing Regions, and covert Date column types
        try:
            activity_lifecycle = activity_lifecycle.rename(columns=COLUMN_RENAME_MAP["Activity Lifecycle"])
            activity_lifecycle = activity_lifecycle[KEEP_COLUMNS_MAP["Activity Lifecycle"]]
        except KeyError:
            raise ColumnSubsetError(STANDARD_ERROR_MESSAGES["ColumnSubsetError"])

        # convert columns to upper case and remove spaces, then subset by these columns
        activity_lifecycle["Claim Status"] = activity_lifecycle["Claim Status"].str.replace(" ", "").str.upper()
        activity_lifecycle["PA Status"] = activity_lifecycle["PA Status"].str.replace(" ", "").str.upper()
        activity_lifecycle["Program"] = activity_lifecycle["Program"].str.replace(" ", "").str.upper()

        activity_lifecycle = activity_lifecycle[~activity_lifecycle["Claim Status"].isin(["DENIED"])]
        activity_lifecycle = activity_lifecycle[activity_lifecycle["PA Status"].isin(["APPROVED", "PENDINGAPPROVAL", "CLOSED"])]
        activity_lifecycle["Region"] = activity_lifecycle["Region"].fillna("NA")

        for column, imputed_value in IMPUTED_VALUES_MAP["Activity Lifecycle"].items():
            activity_lifecycle[column] = activity_lifecycle[column].fillna(imputed_value)

        activity_lifecycle["Activity Start Date"] = pd.to_datetime(activity_lifecycle["Activity Start Date"]).dt.date
        activity_lifecycle["Activity End Date"] = pd.to_datetime(activity_lifecycle["Activity End Date"]).dt.date

        # apply requirements modifications
        activity_lifecycle["Claim Approved in Local Currency"] = activity_lifecycle["Claim Approved Amount (Local)"].apply(
            lambda x: "NOCLAIM" if (pd.isna(x) or x == "") else 0 if x == 0 else x
        )

        return activity_lifecycle

    def __prepare_gbd_tracker(self) -> pd.DataFrame:
        """
        Prepare the GBD Payment Tracker report.

        Use a ReportManager instantiated in main to turn a Excel sheet into a DataFrame.

        Returns
        -------
            pd.DataFrame: A copy of the GBD Payment Tracker, where only select columns have been kept.

        """
        gbd_tracker = self.reports[REPORT_NAMES[1]].copy(deep=True)

        try:
            gbd_tracker = gbd_tracker[KEEP_COLUMNS_MAP["GBD Payment Tracker"]]
        except KeyError:
            raise KeyError(STANDARD_ERROR_MESSAGES["ColumnSubsetError"])

        for column, imputed_value in IMPUTED_VALUES_MAP["GBD Payment Tracker"].items():
            gbd_tracker[column] = gbd_tracker[column].fillna(imputed_value)

        gbd_tracker = gbd_tracker.rename(columns=COLUMN_RENAME_MAP["GBD Payment Tracker"])

        return gbd_tracker

    def __prepare_country_codes(self) -> pd.DataFrame:
        """
        Prepare the Country Codes report.

        Use a ReportManager instantiated in main to turn an Excel sheet into a formatted and cleaned DataFrame.

        Returns
        -------
            pd.DataFrame: A preprocessed Country Codes report.

        """
        country_codes = self.reports[REPORT_NAMES[2]].copy(deep=True)
        try:
            country_codes = country_codes[KEEP_COLUMNS_MAP["Country Codes"]]
        except KeyError:
            raise KeyError(STANDARD_ERROR_MESSAGES["ColumnSubsetError"])

        # drop rows with missing Country Name, remove extraneous "," characters from Country Code
        country_codes = country_codes[country_codes["Country Name"].notna()]
        country_codes["Country Code"] = country_codes["Country Code"].str.replace(",", "")

        # ensure the Company Code and Location Code are three-character strings
        country_codes["Company Code"] = country_codes["Company Code"].astype("Int64").astype(str)
        country_codes["Location Code"] = country_codes["Location Code"].astype("Int64").astype(str)

        # if the Country Code field is not in the country_code report, append it to the report
        for _, row in self.__prepare_activity_lifecycle().iterrows():
            if row["Country"] not in country_codes["Country Code"].to_list():
                new_row = pd.Series([""] * country_codes.shape[1], index=country_codes.columns)
                new_row["Country Code"] = new_row["New Region This Week"] = row["Country"]
                country_codes = country_codes._append(new_row, ignore_index=True)

        country_codes = country_codes.rename(columns=COLUMN_RENAME_MAP["Country Codes"])
        country_codes = country_codes.drop_duplicates(keep="first").sort_values(by="Country Name", ascending=False)

        return country_codes

    def __prepare_activities_table(self) -> pd.DataFrame:
        """
        Prepare the Activities Table.

        Use a ReportManager instantiated in main to turn an Excel sheet into a formatted and cleaned DataFrame.

        Returns
        -------
            pd.DataFrame: A preprocessed Activities Table report.

        """
        activities_table = self.reports[REPORT_NAMES[3]].copy(deep=True)

        # ensure that Cost Center, DR Entry, and CR Entry are strings (with decimals removed)
        activities_table["Cost Center"] = activities_table["Cost Center"].astype("Int64").astype(str)
        activities_table["DR Entry"] = activities_table["DR Entry"].astype("Int64").astype(str)
        activities_table["CR Entry"] = activities_table["CR Entry"].astype("Int64").astype(str)

        # ensure that Cost Center is the correct number of characters
        for idx, cost_center in enumerate(activities_table["Cost Center"]):
            if len(cost_center) < len("000"):
                activities_table["Cost Center"][idx] = cost_center * len("000")

        for column, imputed_value in IMPUTED_VALUES_MAP["Activities Table"].items():
            activities_table[column] = activities_table[column].fillna(imputed_value)

        activities_table = activities_table.rename(columns=COLUMN_RENAME_MAP["Activities Table"])

        return activities_table

    def __add_quarterly_sums(self, monthly_amounts: pd.DataFrame, format_specifier: str) -> pd.DataFrame:
        """
        Add quarterly sum columns to a table of monthly accrual amounts.

        Accept a table whose column headers span a date range of monthly accrual amounts, then add new
        columns to the table that contain the quarterly sums of column values for each quarter's respective
        months.

        Args:
        ----
            monthly_amounts (pd.DataFrame): A table of monthly accrual amounts.
            format_specifier (str): Date specifier used to express month name strings as date objects.

        Returns:
        -------
            pd.DataFrame: The monthly accruals table with quarterly sum columns added.

        """
        datetime_columns = pd.to_datetime(monthly_amounts.columns, format=format_specifier)

        monthly_amount_columns = monthly_amounts.columns
        quarterly_sum_columns = []

        for quarter, group in monthly_amounts.groupby(datetime_columns.to_period("Q"), axis=1):
            # add the respective month columns for the quarter, then add the quarter name column
            quarterly_sum_columns.extend(group.columns)
            quarter_name = f"Q{quarter.quarter} {quarter.year}"

            # calculate the quarterly sum, then add the column name immediately after it's respective month columns
            monthly_amounts[quarter_name] = round(group.sum(axis=1), 2)
            quarterly_sum_columns.append(quarter_name)

        # reorder the columns so the quarterly sums follow their respective months, then restore the original month column names
        monthly_amounts["Total Accrual"] = round(monthly_amounts.iloc[:, : len(monthly_amount_columns)].sum(axis=1), 2)
        monthly_amounts = monthly_amounts[quarterly_sum_columns + ["Total Accrual"]]
        monthly_amounts.columns = [
            col.strftime(format_specifier) if isinstance(col, pd.Timestamp) else col for col in monthly_amounts.columns
        ]

        return monthly_amounts

    @classmethod
    def prepare_accruals_report(
        cls,
        accruals_report: pd.DataFrame,
        monthly_accrual_amounts: pd.DataFrame,
        format_specifier: str = "%B %Y",
    ) -> tuple:
        """
        Prepare the Accruals Report.

        Subset the Accruals Report by columns to keep, sort Monthly Accrual Amounts columns chronologically, and
        replace missing values in the Monthly Accrual Amounts. Then concatenate the Accruals report with the Monthly
        Accrual Amounts.

        Args:
        ----
            accruals_report (pd.DataFrame): The Accruals Report, with columns added in accordance with R2R guidelines.
            monthly_accrual_amounts (pd.DataFrame): A dataframe containing the monthly accrual amounts for each claim.
            format_specifier (str, optional): Date specifier used to express month name strings as date objects. Defaults
                                              to "%B %Y".

        Returns:
        -------
            tuple: A concatenation of the Accruals Report and the Monthly Accrual Amounts, where the concatenation
                   has been subset and missing values replaced. Also, the names of the new quarterly sum columns.

        """
        accruals_report["Intercompany Code"] = ["000"] * len(accruals_report)
        accruals_report["Product Code"] = ["000"] * len(accruals_report)

        try:
            accruals_report = accruals_report[KEEP_COLUMNS_MAP["Accruals Report"]]
        except KeyError:
            raise KeyError(STANDARD_ERROR_MESSAGES["ColumnSubsetError"])

        # add missing months, then sort them chronologically
        for accrual_month in ACCRUAL_MONTHS:
            if accrual_month not in monthly_accrual_amounts.columns:
                monthly_accrual_amounts[accrual_month] = 0.00

        chronological_months = sorted(monthly_accrual_amounts.columns, key=lambda x: dt.datetime.strptime(x, format_specifier))
        monthly_accrual_amounts = monthly_accrual_amounts[chronological_months]

        # fill missing values with 0.00, then add quarterly sum columns
        monthly_accrual_amounts = monthly_accrual_amounts.fillna(0.00)
        monthly_accrual_amounts = cls.__add_quarterly_sums(cls, monthly_accrual_amounts, format_specifier)

        accruals_report = accruals_report.reset_index(drop=True)
        monthly_accrual_amounts = monthly_accrual_amounts.reset_index(drop=True)

        # get the names of the new quarterly sum columns
        accrual_column_names = list(monthly_accrual_amounts.columns)

        return (pd.concat([accruals_report, monthly_accrual_amounts], axis=1), accrual_column_names)

    @staticmethod
    def join_prepared_reports(prepared_reports: list[pd.DataFrame], join_keys: list[str], join_method: str = "left") -> pd.DataFrame:
        """
        Join dataframes on specified join keys.

        Join the dataframes in the prepared_reports parameter on the columns specified by the join_keys list.

        Args:
        ----
            prepared_reports (list[pd.DataFrame]): A list of dataframes, where each element in the list contains a report that is
                                                   to be joined with the base_report.
            join_keys (list[str]): A list of strings specifying the columns the dataframes are to be joined on.
            join_method (str): The type of join to be performed. Defaults to "left".

        Raises:
        ------
            JoinKeyError: If the join keys are not present in both reports that are to be joined.

        Returns:
        -------
            pd.DataFrame: A joined dataframe created by joining the dataframes in the reports parameter on the join_col parameter.

        """
        base_report = prepared_reports[0]
        try:
            for idx, report in enumerate(prepared_reports[1:]):
                join_key = join_keys[idx]
                base_report = base_report.merge(report, on=join_key, how=join_method)

        except KeyError:
            raise JoinKeyError(STANDARD_ERROR_MESSAGES["JoinKeyError"])

        return base_report
