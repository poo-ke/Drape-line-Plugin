import csv
from PyQt5.QtCore import QVariant
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterFile,
    QgsProcessingParameterEnum,
    QgsProcessingParameterString,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterDefinition,
    QgsFields,
    QgsField,
    QgsFeature,
    QgsGeometry,
    QgsProcessingException,
    QgsFeatureSink,
    QgsPointXY
)

class DrapeLineFromCSV(QgsProcessingAlgorithm):
    INPUT = 'INPUT'
    MATCH_FIELD = 'MATCH_FIELD'
    CSV_FILE = 'CSV_FILE'
    UNITS = 'UNITS'
    EXTRA_FIELDS = 'EXTRA_FIELDS'
    OUTPUT = 'OUTPUT'

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT, 'Input line layer', [QgsProcessing.TypeVectorLine]))
        self.addParameter(QgsProcessingParameterField(
            self.MATCH_FIELD, 'Matching field in input layer', parentLayerParameterName=self.INPUT))
        self.addParameter(QgsProcessingParameterFile(
            self.CSV_FILE, 'CSV file with matching field,start,end,...other fields',
            behavior=QgsProcessingParameterFile.File, fileFilter='CSV files (*.csv)'))
        self.addParameter(QgsProcessingParameterEnum(
            self.UNITS, 'Units', options=['Meters', 'Feet'], defaultValue=0))

        try:
            self.addParameter(QgsProcessingParameterString(
                self.EXTRA_FIELDS,
                'Extra CSV fields to import (comma-separated column names)',
                defaultValue='',
                optional=True
            ))
        except TypeError:
            p = QgsProcessingParameterString(
                self.EXTRA_FIELDS,
                'Extra CSV fields to import (comma-separated column names)',
                defaultValue=''
            )
            p.setFlags(p.flags() | QgsProcessingParameterDefinition.FlagOptional)
            self.addParameter(p)

        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT, 'Output line'))

    def name(self): return 'drape_line_from_csv'
    def displayName(self): return 'Drape Line from CSV'
    def group(self): return 'Drape Tools'
    def groupId(self): return 'drapetools'
    def createInstance(self): return DrapeLineFromCSV()

    def shortHelpString(self):
        return """
<b>Drape Line from CSV</b><br><br>
Extracts line segments from a polyline layer based on start and end distances specified in a CSV file. Import a CSV file containing the layer name, start distance, and end distance to extract single or multiple segments from one or more line layers. Supports overlapping segments and can copy additional CSV columns into the output attributes separated by commas.<br><br>

<b>Parameters:</b><br>
<ul>
  <li><b>Input line layer</b>: A polyline layer from which segments will be extracted.</li>
  <li><b>Matching field in input layer</b>: The attribute field used to match rows in the CSV to features in the input layer.</li>
  <li><b>CSV file with match,start,end,...other fields</b>:<br>
      A CSV file structured as:<br>
      <pre>match_value,start_distance,end_distance,field1,field2,...</pre>
      - First column: matches values in the matching field.<br>
      - Second and third columns: define start and end distances (in selected unit).<br>
      - Remaining columns are optional and can be imported as attributes.
  </li>
  <li><b>Units</b>: Choose 'Meters' or 'Feet' for distance interpretation.</li>
  <li><b>Extra CSV fields to import</b>: (Optional) Comma-separated column names to bring into the output.</li>
</ul>

<b>Output:</b><br>
Creates a new line layer containing:<br>
<ul>
  <li>All original attributes of the matched feature</li>
  <li><b>start_dist</b>: Start distance (in original units)</li>
  <li><b>end_dist</b>: End distance (in original units)</li>
  <li><b>length_seg</b>: Length of the extracted segment (in meters)</li>
  <li>Any extra CSV fields you selected</li>
</ul>
"""

    def extractSegment(self, geom, start, end):
        if geom.isMultipart():
            lines = geom.asMultiPolyline()
        else:
            lines = [geom.asPolyline()]
        segment = []
        dist = 0.0
        for line in lines:
            for i in range(len(line) - 1):
                p1, p2 = line[i], line[i + 1]
                seg_len = QgsPointXY(p1).distance(QgsPointXY(p2))
                if seg_len <= 0:
                    continue
                if dist + seg_len < start:
                    dist += seg_len
                    continue
                if not segment:
                    ratio = max(0.0, min(1.0, (start - dist) / seg_len))
                    segment.append(QgsPointXY(
                        p1.x() + (p2.x() - p1.x()) * ratio,
                        p1.y() + (p2.y() - p1.y()) * ratio))
                if dist + seg_len >= end:
                    ratio = max(0.0, min(1.0, (end - dist) / seg_len))
                    segment.append(QgsPointXY(
                        p1.x() + (p2.x() - p1.x()) * ratio,
                        p1.y() + (p2.y() - p1.y()) * ratio))
                    return QgsGeometry.fromPolylineXY(segment)
                segment.append(QgsPointXY(p2))
                dist += seg_len
        return QgsGeometry.fromPolylineXY(segment)

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        match_field = self.parameterAsString(parameters, self.MATCH_FIELD, context)
        csv_path = self.parameterAsFile(parameters, self.CSV_FILE, context)
        units = self.parameterAsEnum(parameters, self.UNITS, context)
        extra_fields_input = self.parameterAsString(parameters, self.EXTRA_FIELDS, context)

        extra_fields = []
        if extra_fields_input:
            extra_fields = [field.strip() for field in extra_fields_input.split(',') if field.strip()]

        unit_factor = 1.0 if units == 0 else 0.3048

        csv_entries = []
        try:
            with open(csv_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                if not reader.fieldnames or len(reader.fieldnames) < 3:
                    raise QgsProcessingException("CSV must have at least three columns: match,start,end")

                for row in reader:
                    try:
                        match_val = row[reader.fieldnames[0]].strip()
                        start = float(row[reader.fieldnames[1]]) * unit_factor
                        end = float(row[reader.fieldnames[2]]) * unit_factor
                        if end <= start:
                            continue
                        extras = [row.get(col, '') for col in extra_fields] if extra_fields else []
                        csv_entries.append((match_val, start, end, extras))
                    except Exception:
                       
                        continue
        except Exception as e:
            raise QgsProcessingException(f'Error reading CSV file: {str(e)}')

        out_fields = QgsFields()
        for f in source.fields():
            out_fields.append(f)
        out_fields.append(QgsField("start_dist", QVariant.Double))
        out_fields.append(QgsField("end_dist", QVariant.Double))
        out_fields.append(QgsField("length_seg", QVariant.Int))

        for ef in extra_fields:
            out_fields.append(QgsField(ef, QVariant.String))

        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context, out_fields, source.wkbType(), source.sourceCrs()
        )

        feats = {str(f[match_field]).strip(): f for f in source.getFeatures()}

        for match_val, start, end, extras in csv_entries:
            feat = feats.get(match_val)
            if not feat:
                continue
            seg_geom = self.extractSegment(feat.geometry(), start, end)
            if not seg_geom or seg_geom.isEmpty():
                continue

            new_feat = QgsFeature(out_fields)
            new_feat.setGeometry(seg_geom)

            attrs = feat.attributes() + [start / unit_factor, end / unit_factor, seg_geom.length()] + extras
            new_feat.setAttributes(attrs)
            sink.addFeature(new_feat)

        return {self.OUTPUT: dest_id}
