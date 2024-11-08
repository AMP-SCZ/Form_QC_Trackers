
import pandas as pd

import os
import sys
import json
parent_dir = "/".join(os.path.realpath(__file__).split("/")[0:-3])
sys.path.insert(1, parent_dir)

from utils.utils import Utils
from qc_forms.form_check import FormCheck
from datetime import datetime
class ClinicalChecks(FormCheck):
    
    def __init__(self, row, timepoint, network, form_check_info):
        super().__init__(timepoint, network,form_check_info)
        self.test_val = 0
        self.call_checks(row)
        self.gf_score_check_vars = {'high':{'global_functioning_social_scale':{
        'chrgfs_gf_social_high':['chrgfs_gf_social_scale','chrgfs_gf_social_low']},
        'global_functioning_role_scale':{'chrgfr_gf_role_low chrgfr_gf_role_high': [
        'chrgfr_gf_role_scole','chrgfr_gf_role_low']}},
                            
        'low': {'global_functioning_social_scale':{
        'chrgfs_gf_social_low':['chrgfs_gf_social_scale','chrgfs_gf_social_high']},
        'global_functioning_role_scale':{'chrgfr_gf_role_low' : [
        'chrgfr_gf_role_scole','chrgfr_gf_role_high']}}}
               
    def __call__(self):
        return self.final_output_list

    def call_checks(self, row):
        self.call_global_function_checks(row)
        self.call_oasis_checks(row)

    def call_global_function_checks(self,row):
        """
        Checks for contradictions in the
        global functioning forms
        """
        report_list = ['Main Report','Non Team Forms']
        for score_type, score_vals in self.gf_score_check_vars.items():
            if score_type == 'low':
                gt_bool = True
            else:
                gt_bool = False
            for form, vars  in score_vals.items():
                for low_score, other_scores in vars.items():
                    var_list = other_scores + [low_score]
                    self.functioning_score_check(row, [form],
                    var_list, {'reports':report_list},
                    bl_filtered_vars=[],filter_excl_vars=True,
                    compared_score_var = low_score, 
                    other_score_vars = other_scores, gt = gt_bool)

    def call_oasis_checks(self, row):
        forms = ['oasis']
        report_list = ['Main Report','Non Team Forms']
        for x in range(2,6):
            oasis_anx_var = f'chroasis_oasis_{x}'
            self.oasis_anxiety_check(row, forms, ['chroasis_oasis_1',oasis_anx_var],
            {'reports': report_list},bl_filtered_vars=[],
                filter_excl_vars=True, anx_var = oasis_anx_var)
        oasis_lifestyle_vars = {'chroasis_oasis_4': 1 , 'chroasis_oasis_5' : 0}
        for oasis_lifestyle_var, cutoff_val in oasis_lifestyle_vars.items():
            self.oasis_lifestyle_check(row, forms, ['chroasis_oasis_3',oasis_lifestyle_var],
            {'reports': report_list}, bl_filtered_vars=[],
            filter_excl_vars=True, lifestyle_var = oasis_lifestyle_var, cutoff = cutoff_val)
            
    @FormCheck.standard_qc_check_filter
    def oasis_anxiety_check(self, row, filtered_forms,
        all_vars, changed_output_vals, bl_filtered_vars=[],
        filter_excl_vars=True, anx_var = ''
    ):
        if row.chroasis_oasis_1 in self.utils.all_dtype([0]):
            anx_var_val = getattr(row,anx_var)
            if (anx_var_val not in (self.utils.missing_code_list + [''])
            and self.utils.can_be_float(anx_var_val)):
                if float(anx_var_val) > 0:
                    return (f'Marked as having'
                            f' no anxiety in chroasis_oasis_1,'
                            f' but {anx_var} is equal to {anx_var_val}')
                
    @FormCheck.standard_qc_check_filter       
    def oasis_lifestyle_check(self, row, filtered_forms,
        all_vars, changed_output_vals, bl_filtered_vars=[],
        filter_excl_vars=True, lifestyle_var = '', cutoff = 0
    ):
        compared_oasis_val = getattr(row,'chroasis_oasis_3')
        lifestyle_var_val = getattr(row,lifestyle_var)
        for var_val in [compared_oasis_val,lifestyle_var_val]:
            if (var_val in self.missing_code_list 
            or not self.utils.can_be_float(var_val)):
                return
        if float(compared_oasis_val) < 2 and float(lifestyle_var_val) > cutoff:
            return (f"chroasis_oasis_3 states that lifestyle"
            f" was not affected, but {lifestyle_var} is greater than {cutoff}")

    @FormCheck.standard_qc_check_filter
    def functioning_score_check(self, row, filtered_forms,
        all_vars, changed_output_vals, bl_filtered_vars=[],
        filter_excl_vars=True, compared_score_var = '',
        other_score_vars = [], gt = True
    ):  
        compared_score_val = getattr(row, compared_score_var)
        if not self.utils.can_be_float(compared_score_val):
            return
        
        for score_var in other_score_vars:
            other_score_val = getattr(row,score_var)
            if self.utils.can_be_float(other_score_val):
                if gt == True and float(compared_score_val) > float(other_score_val):
                    return (f'{compared_score_var} ({compared_score_val}) is'
                    f' not the lowest score ({score_var} = {other_score_val})')
                elif gt == False and float(compared_score_val) < float(other_score_val):
                    return (f'{compared_score_var} ({compared_score_val}) is'
                    f' not the highest score ({score_var} = {other_score_val})')
        
        return 