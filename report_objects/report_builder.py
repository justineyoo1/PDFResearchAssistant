import calendar
from datetime import date, timedelta
from datetime import datetime as dt

import pandas as pd

from mdf_accruals.constants import MONTH_NAME_MAP, PROJECT_CODE_MAP, STANDARD_ERROR_MESSAGES, SUMMARY_ROW_VALUE_MAP, TRANSFORMATION_MAP
from mdf_accruals.report_objects.errors.activity_not_found_error import ActivityNotFoundError
from mdf_accruals.report_objects.errors.column_subset_error import ColumnSubsetError
from mdf_accruals.report_objects.errors.improper_argument_error import ImproperArgumentError
from mdf_accruals.report_objects.report_manager import ReportManager


class ReportBuilder:
    """
    ReportBuilder class.

    ReportBuilder class to instantiate report objects. These can then be used to add columns, perform
    feature-engineering, and manipulate data within a base_report field in order to build the Accruals
    Report.
    """

    def __init__(self, base_report: pd.DataFrame):
        """
        ReportBuilder constructor.

        Initialize a ReportBuilder object by setting the fields to the arguments passed tothe constructor.

        Args:
        ----
            base_report (pd.DataFrame): The join of the Activity Lifecycle, GBD Payment Tracker, Country Code
                                        and Activity Table reports.

        """
        self.base_report = base_report

    def get_base_report(self) -> pd.DataFrame:
        """
        Get the base_report field.

        Return the base_report class field to the calling routine.

        Returns
        -------
            pd.DataFrame: The base_report field.

        """
        return self.base_report

    def build_accruals_report(self, pa_to_claims_factors: pd.DataFrame) -> tuple:
        """
        Enhance the base_report field.

        Add required columns to the base_report field based on the values of existing columns and the
        reporting requirements outlined by the Record to Report team.

        Returns
        -------
            tuple: A copy of the base_report field, where new columns have been appended according to the
                   reporting requirements, as well as a list of the monthly_accrual_amounts column names.

        """
        accruals_report = self.base_report.copy(deep=True)

        # add requested columns using private helper methods
        accruals_report["Claim Invoice or Credit Memo Settlement Status"] = accruals_report.apply(
            lambda x: self.__get_settlement_status(x["Status"]), axis=1
        )
        accruals_report["Cost Center"] = accruals_report.apply(
            lambda x: self.__calculate_cost_center(x["Cost Center"], x["Accounting Category"], x["Program"], x["APPROVAL_BUDGET_FUND"]),
            axis=1,
        )
        accruals_report["Sales Channel"] = accruals_report.apply(
            lambda x: self.__calculate_sales_channel(x["Region"], x["DR Account"], x["Partner Type"]), axis=1
        )
        accruals_report["Project Code"] = accruals_report.apply(
            lambda x: self.__calculate_project_code(x["APPROVAL_BUDGET_NAME"], x["Program"], x["Partner"]), axis=1
        )
        accruals_report["Days to Accrue"] = accruals_report.apply(
            lambda x: self.__calculate_days_to_accrue(x["Activity Start Date"], x["Activity End Date"]), axis=1
        )
        accruals_report["Invoice or Credit Memo Processed in Oracle?"] = accruals_report.apply(
            lambda x: self.__is_processed(x["Claim Invoice or Credit Memo Settlement Status"]), axis=1
        )
        accruals_report["Invoice or Credit Memo Processed Amount (Local Currency)"] = accruals_report.apply(
            lambda x: self.__get_processed_amount(
                x["Invoice or Credit Memo Processed in Oracle?"], x["Convert to Partner Currency - Payment Amount"]
            ),
            axis=1,
        )
        accruals_report[["Total PA Accrual (Local Currency)", "Accrual Reduction Factor"]] = accruals_report.apply(
            lambda x: self.__get_total_pa_accrual(
                x["Activity"],
                x["Claim Status"],
                x["Region"],
                x["Invoice or Credit Memo Processed in Oracle?"],
                x["Approved PA in Local Currency"],
                pa_to_claims_factors,
            ),
            axis=1,
        ).tolist()
        accruals_report["Total Unprocessed Claim Accrual (Local Currency)"] = accruals_report.apply(
            lambda x: self.__get_total_unprocessed_accrual(
                x["Claim Status"],
                x["Invoice or Credit Memo Processed in Oracle?"],
                x["Claim Approved Amount (Local)"],
            ),
            axis=1,
        )
        accruals_report["PA Daily Accrual Rate"] = accruals_report.apply(
            lambda x: self.__calculate_daily_accrual_rates(x["Total PA Accrual (Local Currency)"], x["Days to Accrue"]), axis=1
        )
        accruals_report["Unprocessed Claim Daily Accrual Rate"] = accruals_report.apply(
            lambda x: self.__calculate_daily_accrual_rates(x["Total Unprocessed Claim Accrual (Local Currency)"], x["Days to Accrue"]),
            axis=1,
        )

        # update columns for special cases
        edge_case_methods = [
            self.__update_china_claims,
            self.__update_wipro_claims,
            self.__update_accenture_claims,
            self.__update_odine_claims,
            self.__update_latam_claims,
            self.__update_nokia_claims,
        ]
        for method in edge_case_methods:
            accruals_report = accruals_report.apply(lambda row: method(row), axis=1)

        accruals_report = self.__add_summary_rows(accruals_report, pa_to_claims_factors)

        # get a list of dictionaries containing the monthly accrual amounts
        monthly_accrual_amounts = []
        for _, row in accruals_report.iterrows():
            monthly_accrual_amount = self.__get_monthly_accruals(
                row["Claim Approved in Local Currency"],
                row["PA Daily Accrual Rate"],
                row["Unprocessed Claim Daily Accrual Rate"],
                row["Activity Start Date"],
                row["Activity End Date"],
                row["Summary Row for Repeating PA Numbers"],
            )
            monthly_accrual_amounts.append(monthly_accrual_amount)

        # create a Dataframe from this list, add quarterly sum columns, and concatenate it to the accruals report
        monthly_accrual_amounts = pd.DataFrame(monthly_accrual_amounts)
        accruals_report, accrual_column_names = ReportManager.prepare_accruals_report(accruals_report, monthly_accrual_amounts)

        return (accruals_report, accrual_column_names)

    def __get_settlement_status(self, status: str) -> str:
        """
        Add the "Claim Invoice or Credit Memo Settlement Status" column to the accruals_report.

        Private helper method used to add the "Claim Invoice or Credit Memo Settlement Status"
        column to the accruals_report, based on the value of the "Status" column. If the Status
        is missing or NA, return the string "N/A". Otherwise, return the current value of the
        Status.

        Args:
        ----
            status (str): A string used to represent the value of the "Status" column for a given
                          row within the accruals_report.

        Raises:
        ------
            ImproperArgumentError: If the status parameter is not a str or float type.

        Returns:
        -------
            str: A string representing the "Claim Invoice or Credit Memo Settlement Status"
                 column for a given row within the accruals_report.

        """
        if isinstance(status, float):
            status = "N/A"

        if not isinstance(status, str):
            raise ImproperArgumentError(STANDARD_ERROR_MESSAGES["ImproperArgumentError"])

        return status

    def __calculate_cost_center(self, cost_center: str, accounting_category: str, program: str, approval_budget_fund: str) -> str:
        """
        Add the "Cost Center" column to the accruals_report.

        Private helper method used to add the "Cost Center" column to the accruals_report, based on
        the value of the "Program" column. If the Program is "Alliance COOP", return 479. Otherwise,
        return the current value of the "Cost Center".

        Args:
        ----
            cost_center (str): A string used to represent the value of the "Cost Center" column for
                               a given row within the accruals_report.
            accounting_category (str): A string used to represent the value of the "Accounting Category"
                                       column for a given row within the accruals_report.
            program (str): A string used to represent the value of the "Program" column for a given
                           row within the accruals_report.
            approval_budget_fund (str): A string used to represent the value of the "APPROVAL_BUDGET_FUND"
                                        column for a given row within the accruals_report.

        Raises:
        ------
            ActivityNotFoundError: If the any of the columns from the Activities Table are empty within
                                   the accruals_report
            ImproperArgumentError: If the program or cost_center parameters are not str types.

        Returns:
        -------
            str: A string representing the "Cost Center" column for a given row within the
                 accruals_report.

        """
        if isinstance(accounting_category, float) or isinstance(cost_center, float):
            raise ActivityNotFoundError(STANDARD_ERROR_MESSAGES["ActivityNotFoundError"])

        for parameter in [accounting_category, approval_budget_fund, program, cost_center]:
            if not isinstance(parameter, str):
                raise ImproperArgumentError(STANDARD_ERROR_MESSAGES["ImproperArgumentError"])

        # convert to upper to ignore case
        accounting_category = accounting_category.replace(" ", "").upper()
        program = program.replace(" ", "").upper()
        approval_budget_fund = approval_budget_fund.replace(" ", "").upper()

        if "CGI" in approval_budget_fund and "CY24" in approval_budget_fund:
            cost_center = "353"
        elif "CGI" in approval_budget_fund and "CY25" in approval_budget_fund:
            cost_center = "489"
        elif accounting_category == "SALESEXPENSE" and program == "ALLIANCECOOP":
            cost_center = "479"

        return cost_center

    def __calculate_sales_channel(self, region: str, dr_account: str, partner_type: str) -> str:
        """
        Add the "Sales Channel" column to the accruals_report.

        Private helper method used to add the "Sales Channel" column to the accruals_report, based on
        the values of the "Region", "DR Account", and "Partner Type" columns. If the Region is "APAC"
        and DR Account is 262555, return 41, unless the Partner Type contains "OEM", then return 31.
        Otherwise, return 00.

        Args:
        ----
            region (str): A string used to represent the value of the "Region" column for a given
                          row within the accruals_report.
            dr_account (str): A string used to represent the value of the "DR Account" column for a given
                              row within the accruals_report.
            partner_type (str): A string used to represent the value of the "Partner Type" column for
                                a given row within the accruals_report.

        Raises:
        ------
            ImproperArgumentError: If the region, dr_account, or partner_type parameters are not str
                                   types.

        Returns:
        -------
            str: A string representing the "Sales Channel" column for a given row within the
                 accruals_report.

        """
        # default sales channel is 00, return this for Activities without an assigned DR Account
        sales_channel = "00"
        if isinstance(dr_account, float):
            return sales_channel

        for parameter in [region, dr_account, partner_type]:
            if not isinstance(parameter, str):
                raise ImproperArgumentError(STANDARD_ERROR_MESSAGES["ImproperArgumentError"])

        # convert to upper to ignore case
        region = region.replace(" ", "").upper()
        dr_account = dr_account.replace(" ", "").upper()
        partner_type = partner_type.replace(" ", "").upper()

        if (region == "APAC") and (dr_account == "262555"):
            if "OEM" in partner_type:
                sales_channel = "31"
            else:
                sales_channel = "41"

        return sales_channel

    def __calculate_project_code(self, approval_budget_name: str, program: str, partner: str) -> str:
        """
        Add the "Project Code" column to the accruals_report.

        Private helper method used to add the "Project Code" column to the accruals_report, based on
        the values of the "Program" and "Partner" columns. If the Program is "Alliance COOP", return
        the project code for the corresponding Partner in the PROJECT_CODE_MAP. Otherwise, return the
        default project code of 0000.

        Args:
        ----
            approval_budget_name (str): A string used to represent the value of the "APPROVAL_BUDGET_NAME"
                                        column for a given row within the accruals_report.
            program (str): A string used to represent the value of the "Program" column for a given row
                           within the accruals_report.
            partner (str): A string used to represent the value of the "Partner" column for a given row
                           within the accruals_report.

        Raises:
        ------
            ImproperArgumentError: If the program or partner parameters are not str types.

        Returns:
        -------
            str: A string representing the "Project Code" column for a given row within the accruals_report.

        """
        for parameter in [approval_budget_name, program, partner]:
            if not isinstance(parameter, str):
                raise ImproperArgumentError(STANDARD_ERROR_MESSAGES["ImproperArgumentError"])

        project_code = PROJECT_CODE_MAP["DEFAULT"]

        # convert to upper to ignore case
        partner = partner.upper()
        approval_budget_name = approval_budget_name.replace(" ", "").upper()
        program = program.replace(" ", "").upper()

        alliance_partners = list(PROJECT_CODE_MAP.keys())[:-1]
        if "CGI" in approval_budget_name:
            return PROJECT_CODE_MAP["CGI"]
        elif program == "ALLIANCECOOP":
            for alliance_partner in alliance_partners:
                if alliance_partner in partner:
                    return PROJECT_CODE_MAP[alliance_partner]

        return project_code

    def __calculate_days_to_accrue(self, activity_start_date: dt.date, activity_end_date: dt.date) -> int:
        """
        Add the "Days to Accrue" column to the accruals_report.

        Private helper method used to add the "Days to Accrue" column to the accruals_report, based on the
        values of the "Activity Start Date" and "Activity End Date" columns. Return the number of days
        that fall between the activity_start_date and activity_end_date parameters.

        Args:
        ----
            activity_start_date (dt.date): A date used to represent the value of the "Activity
                                           Start Date" column for a given row within the accruals_report.
            activity_end_date (dt.date): A date used to represent the value of the "Activity End
                                         Date" column for a given row within the accruals_report.

        Raises:
        ------
            ImproperArgumentError: If the activity_start_date or activity_end_date parameters are
                                   not dt.date types.

        Returns:
        -------
            int: An int representing the "Days to Accrue" column for a given row within the accruals_report.

        """
        for parameter in [activity_start_date, activity_end_date]:
            if not isinstance(parameter, date):
                raise ImproperArgumentError(STANDARD_ERROR_MESSAGES["ImproperArgumentError"])

        days_to_accrue = int((activity_end_date - activity_start_date).days + 1)

        return days_to_accrue

    def __is_processed(self, settlement_status: str) -> str:
        """
        Add the "Invoice or Credit Memo Processed in Oracle?" column to the accruals_report.

        Private helper method used to add the "Invoice or Credit Memo Processed in Oracle?" column
        to the accruals_report, based on the value of the "Claim Invoice or Credit Memo Settlement
        Status" column. Return YES if the Status column is "Paid", "Credit Memo Issued", or "Settled
        Through Credit Memo". Otherwise, return NO.

        Args:
        ----
            settlement_status (str): A string used to represent the value of the "Claim Invoice
                                     or Credit Memo Settlement Status" column for a given row
                                     within the accruals_report.

        Raises:
        ------
            ImproperArgumentError: If the status parameter is not a str type.

        Returns:
        -------
            str: A string representing the "Invoice or Credit Memo Processed in Oracle?"
                 column for a given row within the accruals_report.

        """
        if not isinstance(settlement_status, str):
            raise ImproperArgumentError(STANDARD_ERROR_MESSAGES["ImproperArgumentError"])

        # convert to upper to ignore case
        settlement_status = settlement_status.replace(" ", "").upper()

        if settlement_status in ("PAID", "CREDITMEMOISSUED", "SETTLEDTHROUGHCREDITMEMO", "CLAIMCANCELLED", "PROCESSEDBUTNOTYETDUE"):
            is_processed = "YES"
        else:
            is_processed = "NO"

        return is_processed

    def __get_processed_amount(self, processed_in_oracle: str, convert_to_partner_currency: float) -> float:
        """
        Add the "Invoice or Credit Memo Processed Amount (Local Currency)" column to the accruals_report.

        Private helper method used to add the "Invoice or Credit Memo Processed Amount (Local Currency)"
        column to the accruals_report, based on the values of the "Invoice or Credit Memo Processed in
        Oracle?" and "Convert to Partner Currency - Payment Amount" columns. Return the value of "Convert
        to Partner Currency - Payment Amount" if "Invoice or Credit Memo Processed in Oracle?" is YES.
        Otherwise, return 0.00.

        Args:
        ----
            processed_in_oracle (str): A string used to represent the value of the "Invoice or Credit Memo
                                       Processed in Oracle?" column for a given row within the accruals_report.
            convert_to_partner_currency (float): A float used to represent the value of the "Convert to
                                                 Partner Currency - Payment Amount" column for a given row
                                                 within the accruals_report.

        Raises:
        ------
            ImproperArgumentError: If the processed_in_oracle parameter is not a str type, or the
                                   convert_to_partner_currency parameter is not a float type.

        Returns:
        -------
            float: A float representing the "Invoice or Credit Memo Processed Amount (Local Currency)"
                   column for a given row within the accruals_report.

        """
        for parameter, type in {processed_in_oracle: str, convert_to_partner_currency: float}.items():
            if not isinstance(parameter, type):
                raise ImproperArgumentError(STANDARD_ERROR_MESSAGES["ImproperArgumentError"])

        if processed_in_oracle == "YES":
            processed_amount = convert_to_partner_currency
        else:
            processed_amount = 0.00

        return processed_amount

    def __get_total_pa_accrual(
        self,
        activity: str,
        claim_status: str,
        region: str,
        processed_in_oracle: str,
        approved_pa_local_currency: float,
        pa_to_claim_factors: pd.DataFrame,
    ) -> tuple:
        """
        Add the "Total PA Accrual (Local Currency)" column to the accruals_report.

        Private helper method used to add the "Total PA Accrual (Local Currency)" column to the accruals_report,
        based on the values of the "Activity", "Claim Status", "Region", "Invoice or Credit Memo Processed in
        Oracle?" and "Approved PA in Local Currency" columns. If the "Claim Status" is "Hold", "Revise/Resubmit",
        or "Submitted", then return 0.00 if "Invoice or Credit Memo Processed in Oracle?" is "Yes". If "Invoice or
        Credit Memo Processed in Oracle?" is "No", then return "Approved PA in Local Currency" times the "PA to
        Claim Factor" for the given "Activity" and "Region". Otherwise, return an empty string.

        Args:
        ----
            activity (str): A string used to represent the value of the "Activity" column for a given row
                            within the accruals_report.
            claim_status (str): A string used to represent the value of the "Claim Status" column for a given
                                row within the accruals_report.
            region (str): A string used to represent the value of the "Region" column for a given row within
                          the accruals_report.
            processed_in_oracle (str): A string used to represent the value of the "Invoice or Credit Memo
                                       Processed in Oracle?" column for a given row within the accruals_report.
            approved_pa_local_currency (float): A string used to represent the value of the "Approved PA in
                                                Local Currency" column for a given row within the accruals_report.
            pa_to_claim_factors (pd.DataFrame): A dataframe containing the "Activity", "APAC", "EMEA", "LATAM",
                                                and "NA" columns of the Activities Table.

        Raises:
        ------
            ImproperArgumentError: If any of the arguments passed to the method invocation are not of the type
                                   specified within the method header.

        Returns:
        -------
            tuple: A tuple representing the "Total PA Accrual (Local Currency)" column for a given row within
                   the accruals_report, along with the accrual reduction factor.

        """
        for parameter, type in {
            activity: str,
            claim_status: str,
            region: str,
            processed_in_oracle: str,
            approved_pa_local_currency: float,
        }.items():
            if not isinstance(parameter, type):
                raise ImproperArgumentError(STANDARD_ERROR_MESSAGES["ImproperArgumentError"])

        # convert to upper to ignore case
        claim_status = claim_status.replace(" ", "").upper()

        # grab the PA to Claims Factor for the given activity and region
        factors = pa_to_claim_factors[pa_to_claim_factors["Activity"] == activity]
        factor = list(factors[region])[0]

        if claim_status in ("HOLD", "REVISE/RESUBMIT", "SUBMITTED", ""):
            if processed_in_oracle == "YES":
                total_pa_accrual, reduction_factor = (0.00, "")
            else:
                total_pa_accrual, reduction_factor = (round(approved_pa_local_currency * factor, 2), factor)
        else:
            total_pa_accrual, reduction_factor = (0.00, "")

        return (total_pa_accrual, reduction_factor)

    def __get_total_unprocessed_accrual(self, claim_status: str, processed_in_oracle: str, claim_approved_amount_local: float) -> float:
        """
        Add the "Total Unprocessed Claim Accrual (Local Currency)" column to the accruals_report.

        Private helper method used to add the "Total Unprocessed Claim Accrual (Local Currency)" column to
        the accruals_report, based on the values of the "Claim Status", "Invoice or Credit Memo Processed
        in Oracle?" and "Claim Approved Amount (Local)" columns. If the "Claim Status" is "Pending Payment",
        "Payment Processing", or "Paid", then return 0.00 if "Invoice or Credit Memo Processed in Oracle?"
        is "Yes". If "Invoice or Credit Memo Processed in Oracle?" is "No", then return "Claim Approved Amount
        (Local)". Otherwise, return an empty string.

        Args:
        ----
            claim_status (str): A string used to represent the value of the "Claim Status" column for a given
                                row within the accruals_report.
            processed_in_oracle (str): A string used to represent the value of the "Invoice or Credit Memo
                                       Processed in Oracle?" column for a given row within the accruals_report.
            claim_approved_amount_local (float): A string used to represent the value of the "Claim Approved
                                                 Amount (Local)" column for a given row within the accruals_report.

        Raises:
        ------
            ImproperArgumentError: If any of the arguments passed to the method invocation are not of the type
                                   specified within the method header.

        Returns:
        -------
            float: A float representing the "Total Unprocessed Claim Accrual (Local Currency)" column for a
                   given row within the accruals_report.

        """
        for parameter, type in {claim_status: str, processed_in_oracle: str, claim_approved_amount_local: float}.items():
            if not isinstance(parameter, type):
                raise ImproperArgumentError(STANDARD_ERROR_MESSAGES["ImproperArgumentError"])

        # convert to upper to ignore case
        claim_status = claim_status.replace(" ", "").upper()

        if claim_status in ("PENDINGPAYMENT", "PAYMENTPROCESSING", "PAID"):
            if processed_in_oracle == "YES":
                total_unprocessed_accrual = 0.00
            else:
                total_unprocessed_accrual = claim_approved_amount_local
        else:
            total_unprocessed_accrual = 0.00

        return total_unprocessed_accrual

    def __calculate_daily_accrual_rates(self, accrual_amount: float, days_to_accrue: int) -> float:
        """
        Add an accrual rate column to the accruals_report.

        Private helper method used to add an accrual rate column to the accruals_report, based on
        the values of an accrual amount and the "Days to Accrue" column. Return the quotient of
        accrual_amount / days_to_accrue parameters.

        Args:
        ----
            accrual_amount (float): A string used to represent the value of an accrual amount column
                                    for a given row within the accruals_report.
            days_to_accrue (int): A string used to represent the value of the "Days to Accrue" column
                                  for a given row within the accruals_report.

        Raises:
        ------
            ImproperArgumentError: If any of the arguments passed to the method invocation are not of
                                   the type specified within the method header.

        Returns:
        -------
            float: A float representing a daily accrual rate column for a given row within the accruals_report.

        """
        if (not isinstance(accrual_amount, float)) and (not isinstance(accrual_amount, str)):
            raise ImproperArgumentError(STANDARD_ERROR_MESSAGES["ImproperArgumentError"])
        if not isinstance(days_to_accrue, int):
            raise ImproperArgumentError(STANDARD_ERROR_MESSAGES["ImproperArgumentError"])

        if accrual_amount == 0.00:
            daily_accrual_rate = accrual_amount
        else:
            try:
                daily_accrual_rate = round(accrual_amount / days_to_accrue, 2)
            except ZeroDivisionError:
                daily_accrual_rate = 0.00

        return daily_accrual_rate

    def __update_china_claims(self, row: pd.Series) -> pd.Series:
        """
        Private helper method used to update select values for China edge cases.

        Return transformations to the row based on the "Country", "Partner Local Currency", and "Accounting
        Category" columns.

        Args:
        ----
            row (pd.Series): A Series object representing a data row. It must contain at least the "Partner",
                             "Partner Local Currency", and "Accounting Region".

        Returns:
        -------
            pd.Series: A Series object with transformations applied based on the matching "Partner",
                       "Partner Local Currency" and "Accounting Region" value. If no matching requirements,
                       the original row is unchanged.

        """
        components = (row["Country"], row["Partner Local Currency"])
        components = tuple(value.upper().replace(" ", "") for value in components)

        transformation = TRANSFORMATION_MAP["China"].get(components)
        if transformation:
            row["Company Code"] = transformation

        return row

    def __update_wipro_claims(self, row: pd.Series) -> pd.Series:
        """
        Private helper method used to update select values for Wipro edge cases.

        Return transformations to the row based on the "Partner" column.

        Args:
        ----
            row (pd.Series): A Series object representing a data row. It must contain at least the "Partner".

        Returns:
        -------
            pd.Series: A Series object with transformations applied based on the matching "Partner" value. If
                       no matching requirements, the original row is unchanged.

        """
        partner = row["Partner"].upper().replace(" ", "")
        transformation = TRANSFORMATION_MAP["Wipro"].get(partner)

        if transformation:
            for column, value in transformation.items():
                if column in row:
                    row[column] = value

        return row

    def __update_accenture_claims(self, row: pd.Series) -> pd.Series:
        """
        Private helper method used to update select values for Accenture edge cases.

        Return transformations to the row based on the "Partner" column.

        Args:
        ----
            row (pd.Series): A Series object representing a data row. It must contain at least the "Partner".

        Returns:
        -------
            pd.Series: A Series object with transformations applied based on the matching "Partner" value. If
                       no matching requirements, the original row is unchanged.

        """
        partner = row["Partner"].upper().replace(" ", "")
        transformation = TRANSFORMATION_MAP["Accenture"].get(partner)

        if transformation:
            for column, value in transformation.items():
                if column in row:
                    row[column] = value

        return row

    def __update_odine_claims(self, row: pd.Series) -> pd.Series:
        """
        Private helper method used to update select values for Odine edge cases.

        Return transformations to the row based on the "Partner" and "APPROVAL_BUDGET_FUND" columns.

        Args:
        ----
            row (pd.Series): A Series object representing a data row. It must contain at least the key "Partner"
                             and "APPROVAL_BUDGET_FUND" values.

        Returns:
        -------
            pd.Series: A Series object with transformations applied based on the matching "Partner" and
                       "APPROVAL_BUDGET_FUND" values. If no matching requirements, the original row is unchanged.

        """
        partner = row["Partner"].upper().replace(" ", "")
        fund = row["APPROVAL_BUDGET_FUND"].upper().replace(" ", "")

        for (partner_name, fund_name_contains), transformation in TRANSFORMATION_MAP["Odine"].items():
            if partner == partner_name and fund_name_contains in fund:
                for column, value in transformation.items():
                    if column in row:
                        row[column] = value

        return row

    def __update_latam_claims(self, row: pd.Series) -> pd.Series:
        """
        Private helper method used to update select values for LATAM edge cases.

        Return transformations to the row based on the "Region" and "Partner Local Currency" columns.

        Args:
        ----
            row (pd.Series): A Series object representing a data row. It must contain at least the key "Region"
                             and "Partner Local Currency" values.

        Returns:
        -------
            pd.Series: A Series object with transformations applied based on the matching "Region" and "Partner
                       Local Currency". If no matching requirements, the original row is unchanged.

        """
        accounting_region = row["Region"].upper().replace(" ", "")
        partner_local_currency = row["Partner Local Currency"].upper().replace(" ", "")

        for (region_name, local_currency_name), transformation in TRANSFORMATION_MAP["Latam"].items():
            if accounting_region == region_name and partner_local_currency == local_currency_name:
                for column, value in transformation.items():
                    if column in row:
                        row[column] = value

        return row

    def __update_nokia_claims(self, row: pd.Series) -> pd.Series:
        """
        Private helper method used to update select values for Nokia edge cases.

        Return transformations to the row based on the "Region" and "Activity" columns.

        Args:
        ----
            row (pd.Series): A Series object representing a data row. It must contain at least the key "Region"
                             and "Activity" values.

        Returns:
        -------
            pd.Series: A Series object with transformations applied based on the matching "Region" and "Activity".
                       If no matching requirements, the original row is unchanged.

        """
        accounting_region = row["Region"].upper().replace(" ", "")
        activity = row["Activity"].upper().replace(" ", "")

        for (region_name, activity_name), transformation in TRANSFORMATION_MAP["Nokia"].items():
            if accounting_region == region_name and activity in activity_name:
                for column, value in transformation.items():
                    if column in row:
                        row[column] = value

        return row

    def __add_summary_rows(self, accruals_report: pd.DataFrame, pa_to_claim_factors: pd.DataFrame) -> pd.DataFrame:
        """
        Add summary rows to the accruals_report.

        Add summary rows to the accruals_report for each unique PA Number in the report in which multiple claims
        are associated with the same PA Number, the "PA Status" is "Approved" or "Pending Approval", and the "Program"
        is "Alliance COOP". For these groups of claims, the amount to be accrued is determined separate from the
        standard set of rules.

        Args:
        ----
            accruals_report (pd.DataFrame): The base_report field with subsequent columns appended to it using the
                                            helper methods of this class. This dataframe is then passed to this method.
            pa_to_claim_factors (pd.DataFrame): A dataframe containing the "Activity", "APAC", "EMEA", "LATAM", and
                                                "NA" columns of the Activities Table.

        Raises:
        ------
            ImproperArgumentError: If the accruals_report parameter is not a pd.DataFrame type.

        Returns:
        -------
            pd.DataFrame: The accruals_report dataframe with the appropriate summary rows appended to each group of
                          claims corresponding to the same PA Amount.

        """
        if not isinstance(accruals_report, pd.DataFrame):
            raise ImproperArgumentError(STANDARD_ERROR_MESSAGES["ImproperArgumentError"])

        # Initial filtering for claims that might get summary rows.
        # This is the first state of 'repeated_pa_claims'.
        duplicate_mask = accruals_report["PA Number"].duplicated(keep=False)
        repeated_pa_claims = accruals_report[duplicate_mask].copy()

        repeated_pa_claims = repeated_pa_claims[repeated_pa_claims["PA Status"].isin(["APPROVED", "PENDINGAPPROVAL"])]
        repeated_pa_claims = repeated_pa_claims[repeated_pa_claims["Program"] == "ALLIANCECOOP"]

        # column schema of 'repeated_pa_claims'
        # if not groups processed, will be used to create an empty DataFrame with correct columns.
        schema_for_empty_case = repeated_pa_claims.columns.tolist()

        # individual 'unique_pa_claims' using the 'repeated_pa_claims'
        # Rows in accruals_report that are NOT in the current 'repeated_pa_claims'.
        if not repeated_pa_claims.empty:
            # This is your original, concise, and correct method
            unique_pa_claims = pd.concat([accruals_report, repeated_pa_claims]).drop_duplicates(keep=False)
        else:
            unique_pa_claims = accruals_report.copy()

        # process groups from the 'repeated_pa_claims'
        # create a lists of DataFrame slices, one for each unique PA Number.
        pa_number_group_slices = []
        if not repeated_pa_claims.empty:  # Only proceed if there are candidates
            pa_number_group_slices = [
                repeated_pa_claims[repeated_pa_claims["PA Number"] == pa_number].copy()  # Use .copy()
                for pa_number in repeated_pa_claims["PA Number"].unique()
            ]

        processed_groups_list = []
        for group_slice in pa_number_group_slices:  # won't run if pa_number_group_slices is empty
            # ensure group_slice is not empty before accessing
            if group_slice.empty:
                continue

            activity = group_slice["Activity"].iloc[0]
            region = group_slice["Region"].iloc[0]

            reduction_factors = pa_to_claim_factors[pa_to_claim_factors["Activity"] == activity]

            if reduction_factors.empty or region not in reduction_factors.columns:
                print(
                    f"Warning: Reduction factor not found for Activity '{activity}' and Region '{region}'. Skipping summary for this PA group."
                )
                processed_groups_list.append(group_slice)  # fallback just incase
                continue

            reduction_factor = reduction_factors[region].iloc[0]

            # Add a blank row to groupings
            new_row_df = pd.DataFrame([[""] * len(group_slice.columns)], columns=group_slice.columns)
            group_with_blank_row = pd.concat([group_slice, new_row_df], ignore_index=True)

            # Fill the summary row
            filled_group = self.__fill_summary_rows(group_with_blank_row, reduction_factor)
            processed_groups_list.append(filled_group)

        # re-assign 'repeated_pa_claims'
        # hold the claims that have summary rows or be an empty dataframe with correct columns
        if processed_groups_list:
            repeated_pa_claims = pd.concat(processed_groups_list, ignore_index=True)
        else:
            # If no groups were processed, 'repeated_pa_claims' becomes an empty DataFrame
            repeated_pa_claims = pd.DataFrame(columns=schema_for_empty_case)

        # add "Summary Row for Repeating PA Numbers" column to the new 'repeated_pa_claims'
        if not repeated_pa_claims.empty:
            summary_flags = [self.__add_summary_flag(row["PA Status"], row["Claim Number"]) for index, row in repeated_pa_claims.iterrows()]
            repeated_pa_claims["Summary Row for Repeating PA Numbers"] = summary_flags
        else:
            # if repeated_pa_claims is empty, add an empty column with the correct name
            repeated_pa_claims["Summary Row for Repeating PA Numbers"] = pd.Series(dtype="object")

        # Add the summary flag column to 'unique_pa_claims'
        unique_pa_claims["Summary Row for Repeating PA Numbers"] = "NO"

        # concatenation
        #'accruals_report' is reassigned here with combined data
        accruals_report = pd.concat([unique_pa_claims, repeated_pa_claims], ignore_index=True)

        return accruals_report

    def __fill_summary_rows(self, pa_number_group: pd.DataFrame, reduction_factor: float) -> pd.DataFrame:
        """
        Fill empty columns for a given summary row.

        For each column within a summary row of the Accruals Report, fill in the empty cells with the appropriate
        values. Columns with standard default values are filled using the SUMMARY_ROW_VALUE_MAP constant. The
        remaining columns are filled according to custom requirements.

        Args:
        ----
            pa_number_group (pd.DataFrame): A dataframe containing a group of rows with multiple claims against the
                                            same PA Number. An empty summary row appears as the last row in the dataframe.
            reduction_factor (float): An Accrual Reduction Factor associated with the the Region and Activity for each
                                      claim included in the pa_number_group parameter.

        Raises:
        ------
            ImproperArgumentError: If the pa_number_group parameter is not a pd.DataFrame type.

        Returns:
        -------
            pd.DataFrame: The pa_number_group dataframe with the appropriate values populated within each column of the
                          summary row.

        """
        if not isinstance(pa_number_group, pd.DataFrame):
            raise ImproperArgumentError(STANDARD_ERROR_MESSAGES["ImproperArgumentError"])

        try:
            # fill all columns that have default values first
            for column in SUMMARY_ROW_VALUE_MAP["PA"]:
                pa_number_group.loc[len(pa_number_group) - 1, column] = pa_number_group.iloc[0][column]
            for column in SUMMARY_ROW_VALUE_MAP["CLAIM"]:
                pa_number_group.loc[len(pa_number_group) - 1, column] = "MULTIPLE"

            # next, fill the columns that have values that need to be calculated from custom logic
            first_claim_number = pa_number_group.iloc[0]["Claim Number"]
            last_claim_number = pa_number_group.iloc[len(pa_number_group) - 2]["Claim Number"][-1]

            pa_number_group.loc[len(pa_number_group) - 1, "PA Number"] = f"{pa_number_group['PA Number'].iloc[0]}.S"
            pa_number_group.loc[len(pa_number_group) - 1, "Claim Number"] = f"{first_claim_number}-{last_claim_number}.S"

            pa_number_group.loc[len(pa_number_group) - 1, "Invoice or Credit Memo Processed Amount (Local Currency)"] = pa_number_group[
                "Invoice or Credit Memo Processed Amount (Local Currency)"
            ][:-1].sum()

            pa_amount = pa_number_group["Approved PA in Local Currency"].iloc[-1]
            processed_claims = pa_number_group[pa_number_group["Invoice or Credit Memo Processed in Oracle?"] == "YES"]

            pa_number_group.loc[len(pa_number_group) - 1, "Total PA Accrual (Local Currency)"] = round(
                pa_amount * reduction_factor - processed_claims["Invoice or Credit Memo Processed Amount (Local Currency)"].sum(), 2
            )
            pa_number_group.loc[len(pa_number_group) - 1, "Accrual Reduction Factor"] = reduction_factor

            total_pa_accrual = pa_number_group["Total PA Accrual (Local Currency)"].iloc[-1]
            days_to_accrue = pa_number_group["Days to Accrue"].iloc[-1]

            try:
                pa_number_group.loc[len(pa_number_group) - 1, "PA Daily Accrual Rate"] = round(total_pa_accrual / days_to_accrue, 2)
            except ZeroDivisionError:
                pa_number_group.loc[len(pa_number_group) - 1, "PA Daily Accrual Rate"] = 0.00

        except KeyError:
            raise ColumnSubsetError(STANDARD_ERROR_MESSAGES["ColumnSubsetError"])

        # finally, fill the columns that are not applicable to the summary row with "N/A"
        pa_number_group.loc[len(pa_number_group) - 1, "Total Unprocessed Claim Accrual (Local Currency)"] = "N/A"
        pa_number_group.loc[len(pa_number_group) - 1, "Unprocessed Claim Daily Accrual Rate"] = "N/A"

        return pa_number_group

    def __add_summary_flag(self, pa_status: str, claim_number: str) -> str:
        """
        Add the "Summary Row for Repeating PA Numbers" column to the accruals_report.

        Private helper method used to add the "Summary Row for Repeating PA Numbers" column to the accruals_report,
        based on the value of the "PA Status" and "Claim Number" columns.

        Args:
        ----
            pa_status (str): A string used to represent the value of the "PA Status" column for a given row within
                             the accruals_report.
            claim_number (str): A string used to represent the value of the "Claim Number" column for a given row
                                within the accruals_report.

        Returns:
        -------
            str: A string representing the "Summary Row for Repeating PA Numbers" column for a given row within the
                 accruals_report.

        """
        if ".S" in claim_number:
            summary_flag = "YES-SUMMARY"
        elif pa_status == "CLOSED":
            summary_flag = "YES-CLOSED"
        else:
            summary_flag = "YES-REPEATED"

        return summary_flag

    def __get_monthly_accruals(
        self,
        claim_approved_local: float,
        pa_accrual_rate: float,
        unprocessed_accrual_rate: float,
        activity_start_date: dt.date,
        activity_end_date: dt.date,
        summary_flag: str,
    ) -> dict:
        """
        Add the monthly accrual columns to the base report.

        Private helper method used to add the monthly accrual amount columns to the accruals_report,
        based on the accrual rates, and the "Activity Start Date" and "Activity End Date" columns.

        Args:
        ----
            claim_approved_local (float): A float used to represent the value of the "Claim Approved
                                          in Local Currency" column for a given row within the
                                          accruals_report.
            pa_accrual_rate (float): A float used to represent the value of the "PA Daily Accrual Rate"
                                     column for a given row within the accruals_report.
            unprocessed_accrual_rate (float): A float used to represent the value of the "Unprocessed
                                              Claim Daily Accrual Rate" column for a given row within
                                              the accruals_report.
            activity_start_date (dt.date): A date used to represent the value of the "Activity
                                           Start Date" column for a given row within the accruals_report.
            activity_end_date (dt.date): A date used to represent the value of the "Activity End
                                         Date" column for a given row within the accruals_report.
            summary_flag (str): A string used to represent the value of the "Summary Row for Repeating
                                PA Numbers" column for a given row within the accruals_report.

        Raises:
        ------
            ImproperArgumentError: If any of the arguments passed to the method invocation are not of
                                   the type specified within the method header.

        Returns:
        -------
            dict: A dictionary representing the monthly accrual amounts for each month in the accrual
                  period.

        """
        for parameter, type in {
            activity_start_date: date,
            activity_end_date: date,
            summary_flag: str,
        }.items():
            if not isinstance(parameter, type):
                raise ImproperArgumentError(STANDARD_ERROR_MESSAGES["ImproperArgumentError"])

        # initialize local variables
        first_day_start_month = self.__get_first_day_of_month(activity_start_date)
        last_day_end_month = self.__get_last_day_of_month(activity_end_date)

        accrual_dates = pd.date_range(first_day_start_month, last_day_end_month, freq="M")
        monthly_accrued_amount = {}

        # define the appropriate accrual rate, then get the current date
        if summary_flag == "YES-SUMMARY":
            accrual_rate = pa_accrual_rate
        else:
            if claim_approved_local == "NOCLAIM" or claim_approved_local <= 0:
                accrual_rate = pa_accrual_rate
            else:
                accrual_rate = unprocessed_accrual_rate

        # get the number of days to accrue for each month
        for accrual_date in accrual_dates:
            month = accrual_date.month
            key = f"{MONTH_NAME_MAP[month]} {str(accrual_date.year)}"

            # handle all cases, including accruals for partial months
            if month == activity_start_date.month and month == activity_end_date.month:
                days_to_accrue = activity_end_date.day - activity_start_date.day + 1
            elif month == activity_start_date.month:
                days_to_accrue = self.__get_days_in_month(accrual_date) - activity_start_date.day + 1
            elif month == activity_end_date.month:
                days_to_accrue = activity_end_date.day
            else:
                days_to_accrue = self.__get_days_in_month(accrual_date)

            monthly_accrued_amount[key] = round(days_to_accrue * accrual_rate, 2)

        return monthly_accrued_amount

    def __get_first_day_of_month(self, date: dt.date) -> dt.date:
        """
        Return the first day of a month.

        Private helper method used to return a date representing the first day of the month given
        a date object.

        Args:
        ----
            date (dt.date): The date object to get the first day of the month for.

        Returns:
        -------
            dt.date: The first day of the month, as referenced from the date parameter.

        """
        return date.replace(day=1)

    def __get_last_day_of_month(self, date: dt.date) -> dt.date:
        """
        Return the last day of the month.

        Private helper method used to return a date representing the last day of the month given
        a date object.

        Args:
        ----
            date (dt.date): The date object to get the last day of the month for.

        Returns:
        -------
            dt.date: The last day of the month, as referenced from the date parameter.

        """
        # get the next month, then go back to the last day of current month
        next_month = date.replace(day=28) + timedelta(days=4)
        last_day_of_month = next_month - timedelta(days=next_month.day)

        return last_day_of_month

    def __get_days_in_month(self, date: dt.date) -> int:
        """
        Return the number of days in a month.

        Private helper method used to return the number of days in the month represented by the
        date parameter.

        Args:
        ----
            date (dt.date): The date object in which the number of days of the month of the date
                            are to be returned.

        Returns:
        -------
            int: The number of days in the month of the current_date parameter.

        """
        days_in_month = calendar.monthrange(date.year, date.month)[1]

        return days_in_month
