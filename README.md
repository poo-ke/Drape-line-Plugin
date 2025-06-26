# Drape-line-Plugin
The plugin has two algorithms: one that obtains inputs from a CSV file and another that obtains manual inputs which generate a line output. The output drapes over the input layer based on the start and end distances given.

HOW TO USE EXAMPLES

1.The example file has files for use in a single line and multiple lines. The examples can be used to learn how to implement the manual input and .csv files.

2. Save the example file. The folder has shapefiles and respective csv input files.

3. Open QGIS. Go to Plugins and check that Drape Line tools is in installed and is ticked. Check that the plugin appears in the processing toolbox too. The dropdown in the processing toolbox should show the two algorithms, one for CSV inputs and the other for manual input.

4. Add layers as indicated below.

5. For the manual input, open the plugin algorithm, select the input layer. Input the start distance and the end distance. Run

6. Select the plugin algorithm and select the input layer. 
	For the csv input, match the input layer with the input csv as shown below.

		For multiple testing:
		layer = multiple_lines.shp
		Input csv = multiple_lines_input.csv

		For single line testing:
		layer = single_line.shp
		input csv = single_line_input.csv

	Select the heading in the dropdown that matches the column 1 heading in the csv. Run.
