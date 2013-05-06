set -ex

env
locale

python - <<EOP
#!/bin/env python
# -*- coding: utf-8 -*
print(u'The terminal locale supports UTF-8 if you can read this. \u23f2')
EOP
