#!/usr/bin/env python
# A simple script to suck up HTML, convert any images to inline Base64
# encoded format and write out the converted file.
#
# Usage: python standalone_html.py <input_file.html> <output_file.html>
#
# TODO: Consider MHTML format: https://en.wikipedia.org/wiki/MHTML

import os
from bs4 import BeautifulSoup


def guess_type(filepath):
    """
    Return the mimetype of a file, given it's path.

    This is a wrapper around two alternative methods - Unix 'file'-style
    magic which guesses the type based on file content (if available),
    and simple guessing based on the file extension (eg .jpg).

    :param filepath: Path to the file.
    :type filepath: str
    :return: Mimetype string.
    :rtype: str
    """
    try:
        import magic  # python-magic
        return magic.from_file(filepath, mime=True)
    except ImportError:
        import mimetypes
        return mimetypes.guess_type(filepath)[0]

def file_to_base64(filepath):
    """
    Returns the content of a file as a Base64 encoded string.

    :param filepath: Path to the file.
    :type filepath: str
    :return: The file content, Base64 encoded.
    :rtype: str
    """
    import base64
    if os.path.exists(filepath):
        with open(filepath, 'rb') as f:
            encoded_str = base64.b64encode(f.read())
        return encoded_str.decode('utf-8')
    else:
        return "error: image not located"


def make_html_images_inline(in_filepath, out_filepath):
    """
    Takes an HTML file and writes a new version with inline Base64 encoded
    images.

    :param in_filepath: Input file path (HTML)
    :type in_filepath: str
    :param out_filepath: Output file path (HTML)
    :type out_filepath: str
    """
    basepath = os.path.split(in_filepath.rstrip(os.path.sep))[0]
    soup = BeautifulSoup(open(in_filepath, 'r'), 'html.parser')

    # add 
    new_style = soup.new_tag('style')
    new_style.attrs['type']="text/css"

    for head in soup.find_all('head'):
        for link in head.find_all('link'):
            if link.has_attr("rel"):
                if link["rel"][0] == "stylesheet":
                    if link.has_attr("href"):
                        styleref = link["href"]
                        if os.path.exists(styleref):
                            with open(styleref, 'r') as fileid:
                                styletext=fileid.read()
                            styletext = styletext.replace('\t','').replace('\n','')
                            link.decompose()
                            new_style.string = styletext
                            head.append(new_style)


    for img in soup.find_all('img'):
        img_path = os.path.join(basepath, img.attrs['src'])
        mimetype = guess_type(img_path)
        img.attrs['src'] = \
            "data:%s;base64,%s" % (mimetype, file_to_base64(img_path))

    for obj in soup.find_all('object'):
        if obj.has_attr('type') and obj.has_attr('data'):
            if obj["type"] == "image/svg+xml":
                svgdata_file=obj["data"]
                if os.path.exists(svgdata_file):
                    with open(svgdata_file,'r') as infile:
                        svgdata=infile.read()
                    svgclean=svgdata.replace('\n','').replace('\t','').replace('"',"'")
                    #svgclean="<img src=\"image/svg+xml;utf8,"+svgclean + "\"></img>"
                    #new_img = soup.new_tag('img')
                    #new_img.attrs['src']="image/svg+xml;utf8,{}".format(BeautifulSoup(svgclean,'html.parser'))
                    obj.insert_after(BeautifulSoup(svgclean,'html.parser'))
                    #obj.insert_after(new_img)
                    obj.decompose()
            elif obj["type"] == "image/gif":
                svgdata_file=obj["data"]
                if os.path.exists(svgdata_file):
                    mimetype = guess_type(svgdata_file)
                    new_img = soup.new_tag('img')
                    new_img.attrs['src'] = "data:%s;base64,%s" % (mimetype, file_to_base64(svgdata_file))
                    obj.insert_after(new_img)
                    obj.decompose()
                        

    for svgobj in soup.find_all('svg'):
        svgobj.attrs["class"] = "svg-reportlet"

    allsoup=str(soup)

    with open(out_filepath, 'w') as of:
        of.write(str(allsoup))

if __name__ == '__main__':
    import sys
    os.chdir(sys.argv[3])
    make_html_images_inline(sys.argv[1], sys.argv[2])

