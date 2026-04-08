"""
Builds a .sdkmod file containing the mod for distribution. 
This is really just a glorified zip file.
Run this from the root of the project,
and it will create a build/ directory with the .sdkmod file inside.
"""
import zipfile

if __name__ == "__main__":
    files_to_include = ["__init__.py", "pyproject.toml", "legendaries.json"]
    with zipfile.ZipFile("build/LootFilter.sdkmod", 'w') as sdkmod:
        for file in files_to_include:
            sdkmod.write(file, arcname=f"LootFilter/{file}")
