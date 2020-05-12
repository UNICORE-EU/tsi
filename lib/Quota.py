"""
This function retrieves the remaining compute quota for the current user

Reporting format: multiple lines, each of which has
<project_name> <remaining> <percent_remaining> <units>

project_name:       the name of the compute project / accounting budget
remaining:          an integer number representing the remaining 
                    compute time
percent_remaining:  an integer 0-100 representing the percentage of 
                    remaining budget vs the amount that was originally 
                    allocated
Units:              core-h, cpu-h or node-h

(if you cannot or do not want to provide this info, just leave as is or
return an empty string)
"""
def get_quota(config, LOG):
    return "USER -1"

