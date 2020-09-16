from pathlib import Path
from zipfile import ZipFile

project = "autocppapi test site"

extensions = ["sphinxcontrib.doxylink", "documenteer.ext.autocppapi"]

exclude_patterns = ["_build", "_includes", "doxygen.tag", "doxygen.tag.zip"]

# Install the test doxygen.tag file.
base_dir = Path(__file__).parent
zip_tag_path = base_dir / "doxygen.tag.zip"
with ZipFile(zip_tag_path) as tagzip:
    tagzip.extract("doxygen.tag", path=base_dir)
tag_path = base_dir / "doxygen.tag"

doxylink = {"lsstcc": (str(tag_path), "cpp-api")}

documenteer_autocppapi_doxylink_role = "lsstcc"
