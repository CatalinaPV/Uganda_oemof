import os
import ast
import pandas as pd
import numpy as np


def get_optional_required_header(data_type):
    """
    This function returns the header of
    1. scalars and
    2. time series
    along with two lists: optional and required header items

    Parameters
    ----------
    data_type : string
        "scalars" or "timeseries" depending on DataFrame

    Returns
    -------
    header : list
        list of strings with all positions in the header

    optional_header : list
        list of strings with optional positions in the header

    required_header : list
        list of strings with required positions in the header

    """
    if data_type == "scalars":
        # Name of each column in scalars
        header = [
            "id_scal",
            "scenario",
            "name",
            "var_name",
            "carrier",
            "region",
            "tech",
            "type",
            "var_value",
            "var_unit",
            "reference",
            "comment",
        ]
        # Names of optional columns in scalars
        optional_header = ["id_scal", "var_unit", "reference", "comment"]

    elif data_type == "timeseries":
        # Names of all columns in a stacked time series
        header = [
            "id_ts",
            "region",
            "var_name",
            "timeindex_start",
            "timeindex_stop",
            "timeindex_resolution",
            "series",
            "var_unit",
            "source",
            "comment",
        ]

        # Names of optional columns in a stacked time series
        optional_header = [
            "id_ts",
            # "region",
            "var_unit",
            "source",
            "comment",
        ]
    else:
        raise ValueError(
            f"{data_type} is not a valid option of a description of the DataFrame type. "
            f"Please choose between 'scalars' and 'timeseries'."
        )

    # Names of required columns in scalars
    required_header = header.copy()
    for optional in optional_header:
        required_header.remove(optional)

    return header, optional_header, required_header


def load_scalars(path):
    """
    This function loads scalars from a csv file

    Parameters
    ----------
    path : str
        path of input file of csv format
    Returns
    -------
    df : pd.DataFrame
        DataFrame with loaded scalars

    """
    # Get header of scalars
    header, optional_header, required_header = get_optional_required_header("scalars")

    # Get file name
    filename = os.path.splitext(path)[0]

    # Read data
    df = pd.read_csv(path)

    # Save header of DataFrame to variable
    df_header = list(df.columns)

    # Check whether required columns are missing in the DataFrame
    missing_required = list(set(required_header).difference(set(df_header)))

    # Interrupt if required columns are missing and print all affected columns
    if len(missing_required) > 0:
        raise KeyError(
            f"The data in {filename} is missing the required column(s): {missing_required}"
        )

    # Check whether optional columns are missing
    for optional in optional_header:
        if optional not in df_header:
            # ID in the form of numbering is added if "id_scal" is missing
            if optional is optional_header[0]:
                df[optional] = np.arange(0, len(df))
            else:
                newline = "\n"
                # For every other optional column name, an empty array is added with the name as
                # header - A user info is printed
                df[optional] = np.nan
                print(
                    f"User info: The data in {filename} is missing the optional column: "
                    f"{optional}. {newline}"
                    f"An empty column named {optional} is added automatically to the DataFrame."
                )

    # Sort the DataFrame to match the header of the template
    df = df[header]

    return df


def load_timeseries(path):
    """
    This function loads a time series from a csv file

    A stacked and non-stacked time series can be passed.
    If a non-stacked time series is passed, it will be stacked in this function.

    Parameters
    ----------
    path : str
        path of input file of csv format

    Returns
    -------
    df : pd.DataFrame
        DataFrame with loaded time series

    """
    # Get header of time series
    timeseries_header = get_optional_required_header("timeseries")
    header = timeseries_header[0]
    optional_header = timeseries_header[1]
    required_header = timeseries_header[2]

    # Read smaller set of data to check its format
    df = pd.read_csv(path, nrows=3)

    # Check if the format matches the one from the results
    # It has a multiIndex with "from", "to", "type" and "timeindex"
    if (
        "from" in df.columns
        and df["from"][0] == "to"
        and df["from"][1] == "type"
        and df["from"][2] == "timeindex"
    ):
        # As a work around for the multiIndex these four lines are combined in one header
        # The convenion is the following:
        # <type> from <from> to <to>
        # E.g.: flow from BB-biomass-st to BB-electricity
        df_columns = []
        for index, col in enumerate(df.columns):
            # First column is the datetime column with the name timeindex
            if index == 0:
                df_columns.append("timeindex")
            # Assign new header of above mentioned format for each column
            else:
                df_columns.append(df[col][1] + " from " + col + " to " + df[col][0])

        # Read the data, which has the format of the results, skipping the multiIndex
        # and adding the assigned header to each column of the data
        df = pd.read_csv(path, skiprows=3)
        for index, col in enumerate(df.columns):
            df.rename(columns={col: df_columns[index]}, inplace=True)

    # Make sure to only stack the DataFrame if it is not stacked already
    stacked = False
    for item in list(df.columns):
        if item in required_header:
            stacked = True

    if not stacked:
        # Convert timeindex column to datetime format
        df["timeindex"] = pd.to_datetime(df[df.columns[0]])
        # In case there is another datetime series with other header than timeindex,
        # it is redundant and deleted
        if df.columns[0] != "timeindex":
            del df[df.columns[0]]
        # Set timeindex as index
        df = df.set_index("timeindex")

        # Stack time series
        df = stack_timeseries(df)

    else:
        # Read data with stacked time series out of a csv
        df = pd.read_csv(path)

        # Save header of DataFrame to variable
        df_header = list(df.columns)

        # Get file name
        filename = os.path.splitext(path)[0]

        # Check whether required columns are missing in the DataFrame
        missing_required = []
        for required in required_header:
            if required not in df_header:
                if "region" not in required:
                    # Add required columns, that are missing, to a list
                    missing_required.append(required)

        # Interrupt if required columns are missing and print all affected columns
        if len(missing_required) > 0:
            raise KeyError(
                f"The data in {filename} is missing the required column(s): {missing_required}"
            )

        # Set timeindex as default name of timeindex_start index
        # This is necessary if DataFrame is to be unstacked afterwards
        df["timeindex_start"].index.name = "timeindex"
        # Convert to datetime format
        df["timeindex_start"] = pd.to_datetime(df["timeindex_start"])
        df["timeindex_stop"] = pd.to_datetime(df["timeindex_stop"])
        # Convert series values from string to list
        for number, item in enumerate(df["series"].values):
            df["series"].values[number] = ast.literal_eval(item)

    # "region" can be extraced from var_name. Therefore a further
    # required header required_header_without_reg is introduced
    required_header_without_reg = required_header.copy()
    required_header_without_reg.remove("region")
    # If optional columns are missing in the stacked DataFrame
    if (
        list(df.columns) == required_header
        or list(df.columns) == required_header_without_reg
    ) and list(df.columns) != header:
        # ID in the form of numbering is added if "id_ts" is missing
        if optional_header[0] not in df.columns:
            df[optional_header[0]] = np.arange(0, len(df))

        # The region is extracted out of "var_name"
        if required_header[0] not in df.columns:
            region = []
            for row in np.arange(0, len(df)):
                # "BE_BB" is added if both "BE" and "BB" in var_name
                if "BE" in df["var_name"][row] and "BB" in df["var_name"][row]:
                    region.append("BE_BB")
                # "BE" is added if "BE" in var_name
                elif "BE" in df["var_name"][row] and "BB" not in df["var_name"][row]:
                    region.append("BE")
                # "BB" is added if "BB" in var_name
                elif "BE" not in df["var_name"][row] and "BB" in df["var_name"][row]:
                    region.append("BB")
                # An error is raised since the region is missing in var_name
                else:
                    raise ValueError(
                        "The data is missing the region."
                        "Please add BB or BE to var_name column"
                    )
            # Add list with region to DataFrame
            df[required_header[0]] = region

        for num_col in np.arange(1, len(optional_header)):
            # For every other optional column name, an empty array is added with the name as
            # header - A user info is printed
            if optional_header[num_col] not in df.columns:
                df[optional_header[num_col]] = [np.nan] * len(df["series"])

    # Sort the DataFrame to match the header of the template
    df = df[header]

    return df


def save_df(df, path):
    """
    This function saves data to a csv file

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to be saved

    path : str
        Path to save the csv file

    """
    # Save scalars to csv file
    df.to_csv(path, index=False)

    # Print user info
    print(f"User info: The DataFrame has been saved to: {path}.")


def df_filtered(df, key, values):
    """
    This function filters columns of a DataFrame which can be passed
    as scalars and time series.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame
    key : string
        The column's name filtered by
    values : list
        List of a value or values to filter by

    Returns
    -------
    df_agg : pd.DataFrame
        DataFrame with aggregated columns
    """

    # Get header of scalars
    scalars_header = get_optional_required_header("scalars")
    header_scalars = scalars_header[0]
    optional_header_scalars = scalars_header[1]
    required_header_scalars = scalars_header[2]

    # Get header of time series
    timeseries_header = get_optional_required_header("timeseries")
    header_timeseries = timeseries_header[0]
    optional_header_timeseries = timeseries_header[1]
    required_header_timeseries = timeseries_header[2]

    # Save header of DataFrame to variable
    df_header = list(df.columns)

    df_header_required = df_header.copy()
    for item in df_header:
        if item in optional_header_scalars:
            df_header_required.remove(item)
        elif item in optional_header_timeseries:
            df_header_required.remove(item)

    if df_header_required == required_header_scalars:
        # Filter options for scalars
        filter_options = ["scenario", "region", "carrier", "tech", "type", "var_name"]

    elif df_header_required == required_header_timeseries:
        # Filter options for time series
        filter_options = ["region", "var_name"]

    else:
        newline = "\n"
        raise KeyError(
            f"The data you passed is neither a stacked time series nor does it contain scalars. "
            f"{newline}"
            f"Please make sure your data contains the following columns {newline}"
            f"time series: {header_timeseries}{newline}"
            f"scalars: {header_scalars}{newline}"
        )

    # Ensure key is a valid filter option
    if key not in filter_options:
        raise KeyError(
            f"{key} is not a option for a filter."
            f"Please choose of one of these filter options: {filter_options}"
        )

    # Check if key is in header
    if key not in df_header:
        raise KeyError(
            f"Your data is missing the column {key}."
            f"Please provide a complete data set with the required column"
        )

    # Empty DataFrame, which will contain filtered items
    df_filtered_by_value = pd.DataFrame(columns=list(df.columns))

    for value in values:
        if value not in list(df[key]):
            print(f"User info: {value} not found as item in column {key}.")
        else:
            for index, row in df.iterrows():
                if value == df[key][index]:
                    df_filtered_by_value = df_filtered_by_value.append(
                        row, ignore_index=True
                    )

    return df_filtered_by_value


def df_agg(df, key):
    """
    This function aggregates columns of a DataFrame

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame
    key : string
        The column's name aggregated by

    Returns
    -------
    df_agg : pd.DataFrame
        DataFrame with aggregated columns
    """

    # Get header of scalars
    scalars_header = get_optional_required_header("scalars")
    header_scalars = scalars_header[0]
    optional_header_scalars = scalars_header[1]
    required_header_scalars = scalars_header[2]

    # Get header of time series
    timeseries_header = get_optional_required_header("timeseries")
    header_timeseries = timeseries_header[0]
    optional_header_timeseries = timeseries_header[1]
    required_header_timeseries = timeseries_header[2]

    # Save header of DataFrame to variable
    df_header = list(df.columns)

    df_header_required = df_header.copy()
    for item in df_header:
        if item in optional_header_scalars:
            df_header_required.remove(item)
        elif item in optional_header_timeseries:
            df_header_required.remove(item)

    scalars = False
    time_series = False

    if df_header_required == required_header_scalars:

        # Aggregation options for scalars
        scalars = True
        agg_options = ["region", "carrier", "tech"]

    elif df_header_required == required_header_timeseries:
        time_series = True
        # Aggregation options for time series
        agg_options = ["region"]

    else:
        newline = "\n"
        raise KeyError(
            f"The data you passed is neither a stacked time series nor does it contain scalars. "
            f"{newline}"
            f"Please make sure your data contains the following columns {newline}"
            f"time series: {header_timeseries}{newline}"
            f"scalars: {header_scalars}{newline}"
        )

    # Ensure key is a valid aggregation option
    if key not in agg_options:
        raise KeyError(
            f"{key} is not a option for a aggregation."
            f"Please choose of one of these aggregation options: {agg_options}"
        )

    # Check if key is in header
    if key not in df_header:
        raise KeyError(
            f"Your data is missing the column {key}."
            f"Please provide a complete data set with the required column"
        )

    # Empty DataFrame, which will contain aggregated items
    df_agg_by_key = pd.DataFrame(columns=list(df.columns))

    # Get list of all items existing in the column passed with key
    key_list = list(df[key])
    key_list = list(dict.fromkeys(key_list))

    # Begin aggregation of scalars
    if scalars:
        # Get list of all scenarios existing in column scenario
        scenario_list = list(df["scenario"])
        scenario_list = list(dict.fromkeys(scenario_list))

        # Aggregation is done by scenario
        for scenario in scenario_list:
            # Aggregation is further done by key
            for key_item in key_list:
                # Add empty dictionary for results
                results_dict = {}
                # Iterate over each row of the scalars DataFrame
                for index_row in df.iterrows():
                    # Set index of iteration
                    index = index_row[0]
                    # Check if scenario and key of the row match the one of the iteration
                    # over the scenario and all keys, which exist in the DataFrame
                    if df["scenario"][index] == scenario and df[key][index] == key_item:
                        # Aggregate with regard to the variable
                        # Aggregation of capacity
                        if "capacity" in df["var_name"][index]:
                            # If capacity does not exist as a key in the result dictionary
                            # it will be added first
                            if "capacity" not in results_dict.keys():
                                results_dict["capacity"] = 0
                            # Add the value of the capacity to the results dictionary
                            results_dict["capacity"] = (
                                results_dict["capacity"] + df["var_value"][index]
                            )
                        # Aggregation of flows of energy carrier
                        # The energy carrier has to be obtained from var_name because we want to
                        # aggregate the end energy. E.g. wind and solar can be aggregated with
                        # electricity as energy carrier
                        elif "flow" in df["var_name"][index]:
                            # Extract energy carrier out of var_name string
                            energy_carrier = df["var_name"][index].split("_")[2]
                            if "carrier" not in key and "tech" not in key:
                                # If the flow of the respective energy carrier does not exist as
                                # a key in the result dictionary it will be added first
                                if "flow_" + energy_carrier not in results_dict.keys():
                                    results_dict["flow_" + energy_carrier] = 0
                                # If the flow goes "in" energy carrier it will be added to the
                                # same flows
                                if "in" in df["var_name"][index]:
                                    results_dict["flow_" + energy_carrier] = (
                                        results_dict["flow_" + energy_carrier]
                                        + df["var_value"][index]
                                    )
                                # If the flow goes "out" energy carrier it will be subtracted from
                                # the same flows
                                elif "out" in df["var_name"][index]:
                                    results_dict["flow_" + energy_carrier] = (
                                        results_dict["flow_" + energy_carrier]
                                        - df["var_value"][index]
                                    )
                            else:
                                # If the flow of the respective energy carrier does not exist as
                                # a key in the result dictionary it will be added first
                                if (
                                    "flow_"
                                    + energy_carrier
                                    + "_"
                                    + df["carrier"][index]
                                    not in results_dict.keys()
                                ):
                                    results_dict[
                                        "flow_"
                                        + energy_carrier
                                        + "_"
                                        + df["carrier"][index]
                                    ] = 0
                                # If the flow goes "in" energy carrier it will be added to the
                                # same flows
                                if "in" in df["var_name"][index]:
                                    results_dict[
                                        "flow_"
                                        + energy_carrier
                                        + "_"
                                        + df["carrier"][index]
                                    ] = (
                                        results_dict[
                                            "flow_"
                                            + energy_carrier
                                            + "_"
                                            + df["carrier"][index]
                                        ]
                                        + df["var_value"][index]
                                    )
                                # If the flow goes "out" energy carrier it will be subtracted from
                                # the same flows
                                elif "out" in df["var_name"][index]:
                                    results_dict[
                                        "flow_"
                                        + energy_carrier
                                        + "_"
                                        + df["carrier"][index]
                                    ] = (
                                        results_dict[
                                            "flow_"
                                            + energy_carrier
                                            + "_"
                                            + df["carrier"][index]
                                        ]
                                        - df["var_value"][index]
                                    )
                        # Aggregation of costs
                        elif "costs" in df["var_name"][index]:
                            # If costs does not exist as a key in the result dictionary it will
                            # be added first
                            if "costs" not in results_dict.keys():
                                results_dict["costs"] = 0
                            # If the costs go "in" energy carrier it will be added to the
                            # same costs
                            if "in" in df["var_name"][index]:
                                results_dict["costs"] = (
                                    results_dict["costs"] + df["var_value"][index]
                                )
                            # If the costs go "out" energy carrier it will be subtracted from
                            # the same costs
                            elif "out" in df["var_name"][index]:
                                results_dict["costs"] = (
                                    results_dict["costs"] - df["var_value"][index]
                                )
                        # Aggregation of invest
                        elif "invest" in df["var_name"][index]:
                            # If invest does not exist as a key in the result dictionary it will
                            # be added first
                            if "invest" not in results_dict.keys():
                                results_dict["invest"] = 0
                            # If invest goes "in" energy carrier it will be added to the
                            # same invest
                            if "in" in df["var_name"][index]:
                                results_dict["invest"] = (
                                    results_dict["invest"] + df["var_value"][index]
                                )
                            # If invest goes "out" energy carrier it will be subtracted from the
                            # same invest
                            elif "out" in df["var_name"][index]:
                                results_dict["invest"] = (
                                    results_dict["invest"] - df["var_value"][index]
                                )
                        # Aggregation of losses
                        elif "losses" in df["var_name"][index]:
                            # If losses does not exist as a key in the result dictionary it will
                            # be added first
                            if "losses" not in results_dict.keys():
                                results_dict["losses"] = 0
                            # Losses are gathered so far. In future they could be substracted from
                            # the respective flow or capacity
                            results_dict["losses"] = (
                                results_dict["losses"] + df["var_value"][index]
                            )
                        else:
                            newline = "\n"
                            # In case a so far unknown var_name occurs, a ValueError will be
                            # raised and the code will error out with exit code 1
                            var_name = df["var_name"][index]
                            raise ValueError(
                                f"Unknown var_name: {var_name}. {newline}"
                                f"This variable is not implemented in the aggregation. "
                                f"Consider adding it to df_agg function."
                            )

                # Add the results of the dictionary per scenario and per key to new row, which is
                # in the format of scalars DataFrame.
                # Iterate over the results in the dictionary and add the key to the respective
                # column: region, carrier or tech. The other two are set to "All"
                for dict_key, dict_item in results_dict.items():
                    if key == "region":
                        region = key_item
                        carrier = "All"
                        tech = "All"
                    elif key == "carrier":
                        region = "All"
                        carrier = key_item
                        tech = "All"
                    elif key == "tech":
                        region = "All"
                        carrier = "All"
                        tech = key_item

                    # Add new row, which will be appended to the aggregated DataFrame
                    new_row = {
                        "id_scal": None,
                        "scenario": scenario,
                        "name": "Aggregated by " + key,
                        "var_name": dict_key,
                        "carrier": carrier,
                        "region": region,
                        "tech": tech,
                        "type": "All",
                        "var_value": dict_item,
                        "var_unit": "-",
                        "reference": None,
                        "comment": None,
                    }
                    # Append row to the aggregated DataFrame
                    df_agg_by_key = df_agg_by_key.append(new_row, ignore_index=True)

    # Begin aggregation of time series
    if time_series:
        # Aggregation is done by key
        for key_item in key_list:
            # Add empty dictionary for results
            results_dict = {}
            # Iterate over each row of the stacked time series DataFrame
            for index_row in df.iterrows():
                # Set index of iteration
                index = index_row[0]
                # Check if key of the row matches the one of the iteration
                # over all keys, which exist in the DataFrame
                if df[key][index] == key_item:
                    # If series not in results dictionary, it will be added
                    if "series" not in results_dict.keys():
                        results_dict["series"] = [0] * len(df["series"][0])
                    # Aggregate series by adding it to the results dictionary
                    results_dict["series"] = np.add(
                        results_dict["series"], df["series"][index]
                    )
            # Add new row, which will be appended to the aggregated DataFrame
            new_row = {
                "id_ts": None,
                "region": key_item,
                "var_name": "Aggregated by " + key,
                "timeindex_start": df["timeindex_start"][0],
                "timeindex_stop": df["timeindex_stop"][0],
                "timeindex_resolution": df["timeindex_resolution"][0],
                "series": results_dict["series"],
                "var_unit": "-",
                "source": None,
                "comment": None,
            }
            # Append row to the aggregated DataFrame
            df_agg_by_key = df_agg_by_key.append(new_row, ignore_index=True)

    return df_agg_by_key


def check_consistency_timeindex(df, index):
    """
    This function assert that values of a column in a stacked DataFrame are same
    for all time steps

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame for which the time index is checked
    index : string
        Index of values to be checked in the DataFrame

    Returns
    -------
    value : string
        Single value of the series of duplicates

    """
    if index == "timeindex_start":
        name = "start date"
    elif index == "timeindex_stop":
        name = "end date"
    elif index == "timeindex_resolution":
        name = "frequency"

    if np.all(df[index].array == df[index].array[0]):
        value = df[index].array[0]
        if value is None:
            raise TypeError(
                f"Your provided data is missing a {name}."
                f"Please make sure you pass the {name} with {index}."
            )
        else:
            return value
    else:
        raise ValueError(
            f"The {name} of your provided data doesn't match for all entries. "
            f"Please make sure to pass the {name} with {index}."
        )


def stack_timeseries(df):
    """
    This function stacks a Dataframe in a form where one series resides in one row

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame to be stacked

    Returns
    -------
    df_stacked : pandas.DataFrame
        Stacked DataFrame

    """
    _df = df.copy()

    # Assert that _df has a timeindex
    if not isinstance(_df.index, pd.DatetimeIndex):
        raise TypeError(
            "Your data should have a time series as an index of the format "
            "'%Y-%m-%d %H:%M:%S'."
        )

    # Assert that frequency match for all time steps
    if pd.infer_freq(_df.index) is None:
        raise TypeError(
            "No frequency of your provided data could be detected."
            "Please provide a DataFrame with a specific frequency (eg. 'H' or 'T')."
        )

    _df_freq = pd.infer_freq(_df.index)
    if _df.index.freqstr is None:
        print(
            f"User info: The frequency of your data is not specified in the DataFrame, "
            f"but is of the following frequency alias: {_df_freq}. "
            f"The frequency of your DataFrame is therefore automatically set to the "
            f"frequency with this alias."
        )
        _df = _df.asfreq(_df_freq)

    # Stack timeseries
    df_stacked_cols = [
        "var_name",
        "timeindex_start",
        "timeindex_stop",
        "timeindex_resolution",
        "series",
    ]

    df_stacked = pd.DataFrame(columns=df_stacked_cols)

    timeindex_start = _df.index.values[0]
    timeindex_stop = _df.index.values[-1]

    for column in df.columns:
        var_name = column
        timeindex_resolution = _df[column].index.freqstr
        series = [list(_df[column].values)]

        column_data = [
            var_name,
            timeindex_start,
            timeindex_stop,
            timeindex_resolution,
            series,
        ]

        dict_stacked_column = dict(zip(df_stacked_cols, column_data))
        df_stacked_column = pd.DataFrame(data=dict_stacked_column)
        df_stacked = df_stacked.append(df_stacked_column, ignore_index=True)

    # Save name of the index in the unstacked DataFrame as name of the index of "timeindex_start"
    # column of stacked DataFrame, so that it can be extracted from it when unstacked again.
    df_stacked["timeindex_start"].index.name = _df.index.name

    return df_stacked


def unstack_timeseries(df):
    """
    This function unstacks a Dataframe so that there is a row for each value

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame to be unstacked

    Returns
    -------
    df_unstacked : pandas.DataFrame
        Unstacked DataFrame

    """
    _df = df.copy()

    # Assert that frequency match for all time steps
    frequency = check_consistency_timeindex(_df, "timeindex_resolution")
    timeindex_start = check_consistency_timeindex(_df, "timeindex_start")
    timeindex_stop = check_consistency_timeindex(_df, "timeindex_stop")

    # Warn user if "source" or "comment" in columns of stacked DataFrame
    # These two columns will be lost once unstacked
    lost_columns = ["source", "comment"]
    for col in lost_columns:
        if col in list(df.columns):
            print(
                f"User warning: Caution any remarks in column '{col}' are lost after "
                f"unstacking."
            )

    # Process values of series
    values_series = []
    for row in _df.iterrows():
        values_series.append(row[1]["series"])

    values_array = np.array(values_series).transpose()

    # Unstack timeseries
    df_unstacked = pd.DataFrame(
        values_array,
        columns=list(_df["var_name"]),
        index=pd.date_range(timeindex_start, timeindex_stop, freq=frequency),
    )

    # Get and set index name from and to index name of "timeindex_start".
    # If it existed in the origin DataFrame, which has been stacked, it will be set to that one.
    df_unstacked.index.name = _df["timeindex_start"].index.name

    return df_unstacked
