# Third party notices

Exact resolved packages are in requirements.lock and dependency-inventory.json.
License texts copied from installed distributions are in third-party-licenses.
The inventory includes development tools; it is not yet a release-approved SBOM.

PySide6 and Qt are provided under their applicable LGPL/GPL or commercial terms.
The one-folder build keeps Qt shared libraries separately replaceable. Qt source
and licensing information is available at https://code.qt.io/ and
https://doc.qt.io/qt-6/licenses-used-in-qt.html. Preserve license notices and
review corresponding source/relinking obligations before distributing a release.
The application does not prohibit reverse engineering for library debugging.

FFmpeg/ffprobe are externally configured executables, not bundled or copied into
the installer. The local development test tools were downloaded from the Gyan
build linked by ffmpeg.org and verified against the distributor SHA256. The Gyan
essentials distribution includes GPL components. A future bundled FFmpeg build
requires a separate license/source and redistribution review.

The transcription adapter is included, while speech models are not bundled.
PyAV includes FFmpeg shared libraries in its wheel; Qt Multimedia also includes
multimedia support libraries. These differ from the separately configured FFmpeg
command-line tools. Preserve their packaged notices and review all associated
corresponding-source obligations before public distribution. Model licenses must
be reviewed separately. Premiere and Creative Cloud remain separately licensed
Adobe products. The UXP source is provided for development, not as an Adobe-
endorsed or certified plugin. Signing and clean-machine QA remain release gates.
