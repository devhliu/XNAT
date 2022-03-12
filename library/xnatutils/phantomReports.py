import dominate
from dominate.tags import *
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import json
import glob
import datetime
import numpy as np
import nibabel
import itertools
import os
from nilearn import plotting

def create_document(title, stylesheet=None, script=None):
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

def add_float_image(imgid, imgclass, image):
    if imgclass is None:
        m = img(id=imgid, src=image)
    else:
        m = img(id=imgid, cls=imgclass, src=image)

    return m

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
                    snr_val = itemvalue['snr']
                    signal_roi = itemvalue['signal_roi']
                    noise_roi = itemvalue['noise_roi']
                    in_file = itemvalue['in_file']
                    #table_data.append([acqdate, roi_val, space_val, snr_val ])
                    table_data.append([acqdate, roi_val, snr_val, signal_roi, noise_roi, in_file ])
    
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
                    tsnr_val = itemvalue["tsnr_in_roi"]
                    tsnr_file = itemvalue["tsnr_file"]
                    signal_roi = itemvalue["signal_roi"]
                    #table_data.append([acqdate, roi_val, space_val, snr_val ])
                    table_data.append([acqdate, roi_val, tsnr_val,tsnr_file,signal_roi ])
    
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


def writeROIimage(mask_rois, threeDfile, image ):
    combo = None
    for roi in mask_rois:
        roiimg = nibabel.load(roi)
        roidata = roiimg.get_fdata()
        if combo is None:
            combo = roidata
            combo_affine = roiimg.affine
            combo_header = roiimg.header
        else:
            combo=np.add(combo,roidata)

    funcimg = nibabel.load(threeDfile)
    if len(funcimg.header.get_data_shape()) > 3:
        funclist = nibabel.funcs.four_to_three(funcimg)
        threeDfile = funclist[0]

    combo_img = nibabel.Nifti1Image(combo, combo_affine, combo_header)

    display=plotting.plot_roi(combo_img, bg_img=threeDfile)
    display.savefig(image)


def writeStatImage(threeDfile, image, dmode='ortho'):
    display=plotting.plot_stat_map(threeDfile, display_mode=dmode)
    display.savefig(image)  

def createSNRSection(doc,reportdict,modality,imagedir,reportcurr):
    table_columns=['datetime','roi', 'snr', 'signal_roi', 'noise_roi', 'in_file']

    if reportcurr is not None:
        d = div()
        captiontext="{} ROIs used for average SNR".format(modality).capitalize()
        d += h3(captiontext,id='{}_snr_roi_display_h'.format(modality))
        snr_table_data = getSnrData(reportcurr,modality)
        snr_df = pd.DataFrame(snr_table_data, columns=table_columns)
        # tsnr is duplicated across rois! just just pick firts one
        # add roi related to tsnr
        grouped=snr_df.groupby(['roi'])
        for roinum, group in grouped:
            signal_roi = group['signal_roi'].iloc[0]
            noise_roi = group['noise_roi'].iloc[0]
            in_file = group['in_file'].iloc[0]
            image_snr = os.path.join(imagedir, '{}_roi_{}_image_snr.png'.format(roinum,modality))
            writeROIimage([signal_roi, noise_roi], in_file, image_snr)
            f = figure(cls='img-float')
            f += add_float_image('{}_snr_roi_display'.format(modality), None, image_snr)
            f += figcaption('ROI {}'.format(roinum))
            d += f
        doc += d
        with doc:
            newdiv = div(cls='clearfloat')
            
    
    table_data = getSnrData(reportdict,modality)
    df = pd.DataFrame(table_data, columns=table_columns)
    df['date']=df.apply(lambda row: formatDateTime(row,'%Y-%m-%d'), axis=1)

    table_columns=['date','roi', 'snr']
    new_df = df[table_columns]

    # cycle through dates
    grouped=new_df.groupby(['roi'])
    d = div()
    captiontext=("{} SNR Table grouped by ROI".format(modality).capitalize())
    d += h3(captiontext,id='{}_snr_table_h'.format(modality))
    for name, group in grouped:
        snrlist=group.values.tolist()
        d += create_float_table('{}_snr_table'.format(modality), 'snr-table', table_columns, snrlist)

    doc += d

    with doc:
        newdiv= div(cls='clearfloat')
   
    plot_df = new_df.sort_values(by=['date'])
    plot_df.reset_index(drop=True, inplace=True)

    sns.relplot(
        data=plot_df, kind="line",
        x="date", y="snr", col="roi", marker="o",
        facet_kws=dict(sharex=False),
    )

    if modality == "structural":
        snrimage=os.path.join(imagedir,"struct_snr.png")
    else:
        snrimage=os.path.join(imagedir,"func_snr.png")
    plt.savefig(snrimage)    
    doc = add_image(doc, '{}_snr_plot'.format(modality), None, 'Plot of {} SNR'.format(modality), snrimage)
    return doc

def createGeometrySection(doc,reportdict,modality,imagedir):
    table_columns=['datetime','field','value']
    table_data = getGeometryData(reportdict, modality)
    df = pd.DataFrame(table_data, columns=table_columns)

    df['date']=df.apply(lambda row: formatDateTime(row,'%Y-%m-%d'), axis=1)
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
    captiontext=("{} Geometry Tables obtained from affine transform to base {}".format(modality,modality).capitalize())
    d += h3(captiontext,id='{}_geometry_table_h'.format(modality))
    for name, group in grouped:
        geomlist=group.values.tolist()
        d += create_float_table('{}_geometry_table'.format(modality), 'geometry-table', table_columns, geomlist)
    doc += d

    with doc:
        newdiv= div(cls='clearfloat')

    plot_df = new_df_index.sort_values(by=['date'])
    plot_df.reset_index(drop=True, inplace=True)

    sns.relplot(
        data=plot_df, kind="line",
        x="date", y="average_values", col="field",  marker="o",
        facet_kws=dict(sharex=False),
    )  

    geomimage=os.path.join(imagedir,"struct_geom.png")
    plt.savefig(geomimage)
    doc = add_image(doc, '{}_geometry_plot'.format(modality), None, 'Plot of {} Geometry'.format(modality), geomimage)
    return doc

def createTSNRSection(doc,reportdict,modality,imagedir, reportcurr=None):
    table_columns=['datetime','roi', 'tsnr_in_roi', 'tsnr_file', 'signal_roi']

    if reportcurr is not None:
        tsnr_table_data = getTsnrData(reportcurr,modality)
        tsnr_df = pd.DataFrame(tsnr_table_data, columns=table_columns)
        # tsnr is duplicated across rois! just just pick firts one
        tsnr_file = tsnr_df['tsnr_file'].iloc[0]
        tsnrorthoimage=os.path.join(imagedir,"func_tsnr_ortho.png")
        writeStatImage(tsnr_file, tsnrorthoimage, 'tiled')
        doc = add_image(doc, '{}_tsnr_overview'.format(modality), None, 'TSNR overview', tsnrorthoimage)

        d = div()
        captiontext=("{} ROIs used for average TSNR".format(modality).capitalize())
        d += h3(captiontext,id='{}_tsnr_roi_display_h'.format(modality))
        # add roi related to tsnr
        grouped=tsnr_df.groupby(['roi'])
        for roinum, group in grouped:
            signal_roi = group['signal_roi'].iloc[0]
            image_tsnr = os.path.join(imagedir, '{}_roi_{}_image_tsnr.png'.format(roinum,modality))
            writeROIimage([signal_roi], tsnr_file, image_tsnr)
            f = figure(cls='img-float')
            f += add_float_image('{}_tsnr_roi_display'.format(modality),None, image_tsnr)
            f += figcaption('ROI {}'.format(roinum))
            d += f
        doc += d
        with doc:
            newdiv = div(cls='clearfloat')

    table_data = getTsnrData(reportdict,modality)
    df = pd.DataFrame(table_data, columns=table_columns)
    df['date']=df.apply(lambda row: formatDateTime(row,'%Y-%m-%d'), axis=1)

    table_columns=['date','roi', 'tsnr_in_roi']
    new_df = df[table_columns]

    # cycle through dates
    grouped=new_df.groupby(['roi'])
    d = div()
    captiontext=("{} TSNR Table grouped by ROI".format(modality).capitalize())
    d += h3(captiontext,id='{}_tsnr_table_h'.format(modality))
    for name, group in grouped:
        tsnrlist=group.values.tolist()
        d += create_float_table('{}_tsnr_table'.format(modality), 'snr-table', table_columns, tsnrlist)

    doc += d

    with doc:
        newdiv= div(cls='clearfloat')

    plot_df = new_df.sort_values(by=['date'])
    plot_df.reset_index(drop=True, inplace=True)
  
    sns.relplot(
        data=plot_df, kind="line",
        x="date", y="tsnr_in_roi", col="roi", marker="o",
        facet_kws=dict(sharex=False),
    )

    tsnrimage=os.path.join(imagedir,"func_tsnr.png")
    plt.savefig(tsnrimage)    
    doc = add_image(doc, '{}_tsnr_plot'.format(modality), None, 'Plot of {} TSNR'.format(modality), tsnrimage)
    return doc

def createPhantomQCReport(MAXRECS,stylesheet, imagedir, reportdict, reportcurr=None):
    doc = create_document('ACR Medium Phantom QC Report', stylesheet)
    with doc:
        with div(id='links').add(ul()):
            h2('Contents')
            li(a('Structural QC',href='#structuralqc'))
            nested=ul()
            with nested:
                for i in ['structural_snr_roi_display_h', 'structural_snr_table_h', 'structural_snr_plot','structural_geometry_table_h','structural_geometry_plot']:
                    li(a(i.replace('_h','').replace('_',' ').title(), href='#%s' % i))
            li(a('Functional QC',href='#functionalqc'))
            nested=ul()
            with nested:
                for i in [ 'functional_tsnr_overview', 'functional_tsnr_roi_display_h', 'functional_tsnr_table_h', 'functional_tsnr_plot', 'functional_snr_roi_display_h', 'functional_snr_table_h', 'functional_snr_plot']:
                    li(a(i.replace('_h','').replace('_',' ').title(), href='#%s' % i))

    doc += hr()
    doc = create_section(doc, 'structuralqc', None, 'Structural QC')
    doc += hr()
    doc = createSNRSection(doc,reportdict, "structural",imagedir,reportcurr)
    doc += hr()
    doc = createGeometrySection(doc,reportdict, "structural",imagedir)
    doc += hr()
    doc = create_section(doc, 'functionalqc', None, 'Functional QC')
    doc += hr()
    doc = createTSNRSection(doc,reportdict, "functional",imagedir,reportcurr)
    doc += hr()
    doc = createSNRSection(doc,reportdict, "functional",imagedir,reportcurr)
    doc += hr()

    return doc

if __name__ == '__main__':
  
    from standalone_html import *

    final_report_file_json = '/mnt/jsons/ACRMED_20220103_finalreport.json'
    reportcurr = getSortedReportSet([final_report_file_json], 1)

    MAXRECS=3
    report_json_dir='/mnt/jsons'
    reportjson = glob.glob(os.path.join(report_json_dir,'*.json'))
    reportdict = getSortedReportSet(reportjson, MAXRECS)

    CURRENTDIR=os.getcwd()
    os.chdir('/mnt')

    doc = createPhantomQCReport(MAXRECS,'./style.css', './images', reportdict, reportcurr)
    final_report_html = '/mnt/final.html'
    final_report_inline_html = '/mnt/final_inline.html'
    with open(final_report_html, 'w') as file:
        file.write(doc.render())
    make_html_images_inline(final_report_html, final_report_inline_html)
