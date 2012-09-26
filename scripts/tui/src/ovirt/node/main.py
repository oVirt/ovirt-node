"""
Create an application instance an start it.
"""

import ovirt.node.app


if __name__ == '__main__':
    app = ovirt.node.app.Application()
    app.run()
