import pandas as pd

import os
import sys
import json
import random
parent_dir = "/".join(os.path.realpath(__file__).split("/")[0:-2])
sys.path.insert(1, parent_dir)

from utils.utils import Utils
from datetime import datetime


"""
cols to match : subject, displayed timepoint, displayed form, displayed variable, error message
if row exists in current output and not at all in old
    append date detected as today

if row exists in old output and not new
     if the most recent date resolved is after the most recent date detected and neither are blank, ignore it
     if the most recent date detected is after the most recent date resolved and neither are blank, append today's date to the date resolved, set currently_resolved to False
     if date detected is not blank and date resolved is blank, append today's date to date resolved, set currently_resolved to True

if row exists in both outputs
    if it is currently resolved in the old one, append today's date to dates detected and change currently_resolved to False
    If it is currently not resolved in the old one, replace it with the new one (so other columns like subject's current timepoint get updated)
"""

class CalculateResolvedErrors():

    def __init__(self):
        self.old_path = '/PHShome/ob001/anaconda3/refactored_qc/output/combined_outputs/old_output/combined_qc_flags.csv'
        self.new_path = '/PHShome/ob001/anaconda3/refactored_qc/output/combined_outputs/new_output/combined_qc_flags.csv'
        self.new_output = []
        self.utils = Utils()
        self.absolute_path = self.utils.absolute_path

        with open(f'{self.absolute_path}/config.json','r') as file:
            self.config_info = json.load(file)

        self.output_path = self.config_info['paths']['output_path']
        self.old_output_csv_path = f'{self.output_path}combined_outputs/old_output/combined_qc_flags.csv'
        self.new_output_csv_path = f'{self.output_path}combined_outputs/new_output/combined_qc_flags.csv'
        self.dropbox_data_folder = f'{self.output_path}formatted_outputs/dropbox_files/'


    def run_script(self):
        if os.path.exists(self.old_output_csv_path):
            print('exists')
            self.determine_resolved_rows()

    def read_dropbox_data(self):
        # define columns to read over
        # match formatted spreadsheet to old one by the sheet name,
        # subject','displayed_timepoint', and displayed_form
        # for any rows in the old df that match those, pull the necessary columns 
        # then save this as the old df again and compare to the new df
        # when comparing to the new df, make sure those columns from the old df are preserved in all conditions

        dbx = self.utils.collect_dropbox_credentials()

        dropbox_path = f'/Apps/Automated QC Trackers/refactoring_tests'
        for entry in dbx.files_list_folder(dropbox_path).entries:
            print(entry.name)
            if entry.name != f'AMPSCZ_Output.csv':
                continue
            _, res = dbx.files_download(dropbox_path + f'/{entry.name}')
            data = res.content
            with open(f'self.dropbox_data_folder/test.csv', "wb") as f:
                f.write(data)

        columns_to_read = ['manually_resolved']
        output_list = []
        df = pd.read_csv('/PHShome/ob001/anaconda3/refactored_qc/form_qc_trackers/main/generate_reports/test.csv',keep_default_na = False)
        cols_to_keep = ['error_message','displayed_variable','displayed_form',
        'displayed_timepoint','subject','manually_resolved']
        cols_to_split = ['error_message','displayed_variable']
        all_columns = df.columns
        for row in df.itertuples():
            if row.manually_resolved == '':
                continue
            splt_col_vals = {}
            for splt_col in cols_to_split:
                splt_col_vals[splt_col] = (getattr(row, splt_col)).split(' | ')
            for ind in range(0,len(splt_col_vals['error_message'])):
                print(ind)
                print(row.manually_resolved)
                curr_row_output = {}
                for col in all_columns:
                    curr_row_output[col] = getattr(row, col)
                for splt_col in cols_to_split:
                    curr_row_output[splt_col] = splt_col_vals[splt_col][ind]
                print(curr_row_output)
                output_list.append(curr_row_output)
        
        output_df = pd.DataFrame(output_list)
        cols_to_keep = [col for col in cols_to_keep if col in output_df.columns]
        print(cols_to_keep)
        print(output_df.columns)

        output_df = output_df[cols_to_keep]
        output_df.to_csv('manualtest.csv')
        prev_output_df = pd.read_csv(self.old_output_csv_path,keep_default_na = False)
        new_df_cols = [col for col in prev_output_df.columns if col not in columns_to_read]

        prev_output_df = prev_output_df[new_df_cols]
        prev_output_df.to_csv('prevetest.csv')

        merged = prev_output_df.merge(output_df, on=['displayed_variable',
        'displayed_form','displayed_timepoint','subject','error_message'], how = 'left')
        print(merged[merged['subject']=='GA04102']['manually_resolved'])

        merged.to_csv('reversed_test.csv', index = False)

    def determine_resolved_rows(self):
        new_df = pd.read_csv(self.new_path, keep_default_na = False)
        old_df = pd.read_csv(self.old_path, keep_default_na = False)
        #new_df = new_df.drop('NDA Excluder', axis=1)
        #old_df = old_df.drop('NDA Excluder', axis=1)

        orig_columns = list(new_df.columns)

        cols_to_merge = ['subject', 'displayed_form', 'displayed_timepoint',
        'displayed_variable','error_message']

        merged = old_df.merge(new_df,
        on = cols_to_merge, how='outer', suffixes = ('_old','_new'))

        merged = merged.fillna('')

        curr_date = str(datetime.today().date())
        for row in merged.itertuples():
            #print(row.Index)
            
            curr_row_output = {}
            if row.network_new != '' and row.network_old == '':
                curr_row_output['currently_resolved'] = False
                curr_row_output['dates_detected'] = self.append_formatted_list(
                row.dates_detected_old, curr_date)
                
                curr_row_output = self.append_all_cols(
                row, curr_row_output, orig_columns, '_new',cols_to_merge,merged)
                
            elif row.network_old != '':
                if row.network_new == '':
                    if row.currently_resolved_old == True:
                        curr_row_output = self.append_all_cols(row, curr_row_output,
                        orig_columns, '_old',cols_to_merge,merged)
                    else:
                        curr_row_output['currently_resolved'] = True
                        curr_row_output['dates_resolved'] = self.append_formatted_list(
                        row.dates_resolved_old, curr_date)
                        curr_row_output = self.append_all_cols(row, curr_row_output,
                        orig_columns, '_old',cols_to_merge,merged)

                elif row.network_new != '':
                    curr_row_output['currently_resolved'] = False
                    if row.currently_resolved_old == True:
                        curr_row_output['dates_detected'] = self.append_formatted_list(
                        row.dates_detected_old, curr_date)
                        
                    for old_col in ['dates_resolved', 'dates_detected']:
                        if old_col not in curr_row_output.keys():
                            curr_row_output[old_col] = getattr(row, old_col + '_old')

                    curr_row_output = self.append_all_cols(row,
                    curr_row_output, orig_columns, '_new',cols_to_merge,merged)

            dates_detected = curr_row_output['dates_detected'].split(' | ')
            most_recent_detection = dates_detected[-1]
            curr_row_output['time_since_last_detection'] = self.utils.days_between(
            str(most_recent_detection))

            self.new_output.append(curr_row_output)
                #if row.currently_resolved
                #curr_row_output['currently_resolved'] = True
        new_df = pd.DataFrame(self.new_output)
        new_df.to_csv(self.new_output_csv_path, index = False)

    def append_formatted_list(self, curr_list_string, item_to_append):
        new_list = []
        if curr_list_string == '':
            return item_to_append
        else:
            new_list = curr_list_string.split(' | ')
            new_list.append(item_to_append)
            new_list_string = ' | '.join(new_list)

            return new_list_string
            
    def append_all_cols(self, row, curr_row_output, all_cols, suffix, merged_cols,df):
        for col in all_cols:
            if col not in curr_row_output.keys():
                if col not in merged_cols:
                    if (col + suffix) in df.columns:
                        curr_row_output[col] = getattr(row, col + suffix)
                else:
                    curr_row_output[col] =  getattr(row, col)

        return curr_row_output

if __name__ =='__main__':
    CalculateResolvedErrors().run_script()