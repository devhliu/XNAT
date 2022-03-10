import dominate
from dominate.tags import *
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import json
import glob
import datetime
import numpy as np
import itertools

def create_page(title, stylesheet=None, script=None):
    doc = dominate.document(title = title)
    if stylesheet is not None:
        with doc.head:
            link(rel='stylesheet',href=stylesheet)
    if script is not None:
        with doc.head:
            script(type='text/javascript',src=script)
    with doc:
        with div(id='header'):
            h1(title)
            p('Report generated on {}'.format(datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%dT%H:%M:%S.%f')) )
    return doc

def create_section(doc, divid, divclass, captiontext):
    with doc:
        if divclass is None:
            d = div(id=divid)
        else:
            d = div(id=divid, cls=divclass)
        with d:
            h2(captiontext)
    return doc


def create_table(doc, divid, divclass, tabid, tabclass, headers, captiontext, reportlist):
    with doc:
        if divclass is None:
            d = div(id=divid)
        else:
            d = div(id=divid, cls=divclass)
        with d:
            h3(captiontext)
            if tabclass is None:
                t = table(id = tabid)
            else:
                t = table(id = tabid, cls = tabclass)
            with t:
                with thead():
                    with tr():
                        for header in headers:
                            th(header)
                with tbody():
                    for listitem in reportlist:
                        with tr():
                            for itemvalue  in listitem:
                                td(itemvalue)
    return doc

def create_float_table(tabid, tabclass, headers, reportlist):
    if tabclass is None:
        t = table(id = tabid)
    else:
        t = table(id = tabid, cls = tabclass)
    with t:
        with thead():
            with tr():
                for header in headers:
                    th(header)
        with tbody():
            for listitem in reportlist:
                with tr():
                    for itemvalue  in listitem:
                        td(itemvalue)
    return t

def add_image(doc, divid, divclass, captiontext, image):
    with doc:
        if divclass is None:
            d = div(id=divid)
        else:
            d = div(id=divid, cls=divclass)
        with d:
            h3(captiontext)
            img(src=image)
    return doc

def getSnrData(reportdict, modality):
    table_data=[]
    for keydate, rep in reportdict.items():
        with open (rep, 'r') as file:
            rep_json = json.load(file)
        acqdate=rep_json[modality]["DateTime"]
        snr=rep_json[modality]["snr"]

        for itemkey, itemvalue in snr.items():
            roi_val = itemkey
            for itemkey, itemvalue in itemvalue.items():
                space_val = itemkey
                # only insert base_space; remove this if statement for both spaces
                if space_val == 'base_space':
                    for itemkey, itemvalue in itemvalue.items():
                        if itemkey ==  'snr' or itemkey == 'snr_native':
                            snr_val = itemvalue
                            #table_data.append([acqdate, roi_val, space_val, snr_val ])
                            table_data.append([acqdate, roi_val, snr_val ])
    
    return table_data

def getTsnrData(reportdict, modality):
    table_data=[]
    for keydate, rep in reportdict.items():
        with open (rep, 'r') as file:
            rep_json = json.load(file)
        acqdate=rep_json[modality]["DateTime"]
        snr=rep_json[modality]["tsnr"]

        for itemkey, itemvalue in snr.items():
            roi_val = itemkey
            for itemkey, itemvalue in itemvalue.items():
                space_val = itemkey
                # only insert base_space; remove this if statement for both spaces
                if space_val == 'base_space':
                    for itemkey, itemvalue in itemvalue.items():
                        if itemkey ==  'tsnr_in_roi' or itemkey == 'tsnr_in_roi_native':
                            snr_val = itemvalue
                            #table_data.append([acqdate, roi_val, space_val, snr_val ])
                            table_data.append([acqdate, roi_val, snr_val ])
    
    return table_data

def getSortedReportSet(reportjson, numitems=None):
    reportjson_dict={}
    for rep in reportjson:
        with open (rep, 'r') as file:
            rep_json = json.load(file)
        acqdate=rep_json["structural"]["DateTime"]
        reportjson_dict[acqdate]=rep

    sorted_dict = dict(sorted(reportjson_dict.items(),reverse=True))

    if numitems is not None and numitems < len(sorted_dict):
        sorted_dict = dict(itertools.islice(sorted_dict.items(), numitems))

    return sorted_dict
    


def getGeometryData(reportdict, modality):
    table_data=[]
    for keydate, rep in reportdict.items():
        with open (rep, 'r') as file:
            rep_json = json.load(file)
        acqdate=rep_json[modality]["DateTime"]
        geom=rep_json[modality]["geometry"]

        for itemkey, itemvalue in geom.items():
            if itemkey ==  'determinant' or itemkey == 'average_scaling' or itemkey == 'scales' or itemkey == 'skews':
                if isinstance(itemvalue,list):
                    itemvalue=str(itemvalue)
                table_data.append([acqdate, itemkey, itemvalue ])
    
    return table_data


def formatDateTime(row, fmt):
    dt = datetime.datetime.strptime(row['datetime'],'%Y-%m-%dT%H:%M:%S.%f')
    return datetime.datetime.strftime(dt, fmt)

def returnAverage(row):
    if len(str(row['value']).split(',')) > 1:
        row_values= [float(x) for x in row['value'].replace('[','').replace(']','').replace(' ','').split(',')]
        return np.mean(np.asarray(row_values))
    else:
        return row['value']

def createSNRSection(doc,reportdict,modality,image):
    table_columns=['datetime','roi', 'snr']
    table_data = getSnrData(reportdict,modality)
    df = pd.DataFrame(table_data, columns=table_columns)
    df['date']=df.apply(lambda row: formatDateTime(row,'%m-%d-%y'), axis=1)

    table_columns=['date','roi', 'snr']
    new_df = df[table_columns]

    # cycle through dates
    grouped=new_df.groupby(['roi'])
    d = div()
    captiontext=("{} SNR Table grouped by ROI".format(modality))
    d += h3(captiontext)
    for name, group in grouped:
        snrlist=group.values.tolist()
        d += create_float_table('{}_snr_table'.format(modality), 'snr-table', table_columns, snrlist)

    doc += d

    with doc:
        newdiv= div(cls='clearfloat')
  
    sns.relplot(
        data=new_df, kind="line",
        x="date", y="snr", col="roi", marker="o",
        facet_kws=dict(sharex=False),
    )

    plt.savefig(image)    
    doc = add_image(doc, '{}_snr_plot'.format(modality), None, 'Plot of {} SNR'.format(modality), image)
    return doc

def createGeometrySection(doc,reportdict,modality,image):
    table_columns=['datetime','field','value']
    table_data = getGeometryData(reportdict, modality)
    df = pd.DataFrame(table_data, columns=table_columns)

    df['date']=df.apply(lambda row: formatDateTime(row,'%m-%d-%y'), axis=1)
    table_columns=['date','field', 'value']
    new_df = df[table_columns]

    # drop row
    new_df['average_values']=new_df.apply(lambda row: returnAverage(row), axis=1)
    new_df_index=new_df.set_index("field")
    new_df_index=new_df_index.drop("average_scaling")
    new_df_index=new_df_index.reset_index()

    # cycle through fields
    table_columns=['date','field', 'value','average_values']
    grouped=new_df.groupby(['field'])
    d = div()
    captiontext=("{} Geometry Tables obtained from affine transform to base ROI".format(modality))
    d += h3(captiontext)
    for name, group in grouped:
        geomlist=group.values.tolist()
        d += create_float_table('{}_geometry_table'.format(modality), 'geometry-table', table_columns, geomlist)
    doc += d

    with doc:
        newdiv= div(cls='clearfloat')


    sns.relplot(
        data=new_df_index, kind="line",
        x="date", y="average_values", col="field",  marker="o",
        facet_kws=dict(sharex=False),
    )  

    plt.savefig(image)
    doc = add_image(doc, '{}_geometry_plot'.format(modality), None, 'Plot of {} Geometry'.format(modality), image)
    return doc

def createTSNRSection(doc,reportdict,modality,image):
    table_columns=['datetime','roi', 'tsnr']
    table_data = getTsnrData(reportdict,modality)
    df = pd.DataFrame(table_data, columns=table_columns)
    df['date']=df.apply(lambda row: formatDateTime(row,'%m-%d-%y'), axis=1)

    table_columns=['date','roi', 'tsnr']
    new_df = df[table_columns]

    # cycle through dates
    grouped=new_df.groupby(['roi'])
    d = div()
    captiontext=("{} TSNR Table grouped by ROI".format(modality))
    d += h3(captiontext)
    for name, group in grouped:
        tsnrlist=group.values.tolist()
        d += create_float_table('{}_tsnr_table'.format(modality), 'snr-table', table_columns, tsnrlist)

    doc += d

    with doc:
        newdiv= div(cls='clearfloat')
  
    sns.relplot(
        data=new_df, kind="line",
        x="date", y="tsnr", col="roi", marker="o",
        facet_kws=dict(sharex=False),
    )

    plt.savefig(image)    
    doc = add_image(doc, '{}_tsnr_plot'.format(modality), None, 'Plot of {} TSNR'.format(modality), image)
    return doc

##################################
# start creation of web page
doc = create_page('ACR Medium Phantom QC', './style.css')
with doc:
    with div(id='links').add(ul()):
        h2('Contents')
        li(a('Structural QC',href='#structuralqc'))
        nested=ul()
        with nested:
            for i in ['structural_snr_table', 'structural_snr_plot','structural_geometry_table','structural_geometry_plot']:
                li(a(i.title(), href='#%s' % i))
        li(a('Functional QC',href='#functionalqc'))
        nested=ul()
        with nested:
            for i in ['functional_tsnr_table', 'functional_tsnr_plot', 'functional_snr_table', 'functional_snr_plot']:
                li(a(i.title(), href='#%s' % i))

doc += hr()


# get all reports
MAXRECS=2
reportjson = glob.glob("./jsons/*.json")
reportdict = getSortedReportSet(reportjson, MAXRECS)

doc = create_section(doc, 'structuralqc', None, 'Structural QC')
doc += hr()
doc = createSNRSection(doc,reportdict, "structural","./images/struct_snr.png")
doc += hr()
doc = createGeometrySection(doc,reportdict, "structural","./images/struct_geom.png")
doc += hr()
doc = create_section(doc, 'functionalqc', None, 'Functional QC')
doc += hr()
doc = createTSNRSection(doc,reportdict, "functional","./images/func_tsnr.png")
doc += hr()
doc = createSNRSection(doc,reportdict, "functional","./images/func_snr.png")
doc += hr()

with open('report.html', 'w') as file:
    file.write(doc.render())