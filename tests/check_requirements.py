"""Reject source updates that need dependencies absent from the pinned image."""
from importlib import metadata
from pathlib import Path
from packaging.requirements import Requirement

checked=[]
for raw in Path('/upstream/requirements.txt').read_text().splitlines():
    line=raw.partition('#')[0].strip()
    if not line:
        continue
    requirement=Requirement(line)
    if requirement.marker and not requirement.marker.evaluate():
        continue
    installed=metadata.version(requirement.name)
    assert requirement.specifier.contains(installed,prereleases=True), (requirement.name,installed,str(requirement.specifier))
    checked.append(f'{requirement.name}=={installed}')
print('PASS: upstream requirements are satisfied by the pinned image:',', '.join(checked))
