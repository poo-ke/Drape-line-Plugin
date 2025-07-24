Example files for single input and multiple input
Open QGIS. Go to Plugins and check that Drape Line tools is in installed and is ticked. Check that the plugin appears in the processing toolbox too. 
The dropdown in the processing toolbox should show the two algorithms, one for CSV inputs and the other for manual input.

For the manual input, open the plugin algorithm, select the input layer. Input the start distance and the end distance. Run

For the csv input, match the input layer with the input csv as shown below.

		For multiple testing:
		layer = multiple_lines.shp
		Input csv = multiple_lines_input.csv

		For single line testing:
		layer = single_line.shp
		input csv = single_line_input.csv

Select the heading in the dropdown that matches the column 1 heading in the csv. Run.
