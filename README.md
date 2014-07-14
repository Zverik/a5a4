# Web interface to pdftk and pdfjam

Those tools are the best for managing PDF pages. But they have two major drawbacks:

1. PDFjam installs to 430 MB (because of texlive dependency), which is a lot.
2. They are not available on Windows.

For casual PDF processing it would be nice to have a web service, which receives some
PDFs and processes them with those tools. This service was specifically aimed at
stitching A5 pages into A4 printer-ready documents.

## CGI

The simplest is the CGI interface. It consists of a plain HTML file to be placed
anywhere in a document root and of python CGI script for `/cgi-bin` directory.
Check paths to pdftk and pdfjam in the script — and you're ready to go.

## Author and license

The script was written by Ilya Zverev and published under WTFPL license.
