echo off
set raw_file_folder=%~1
set extracted_file_folder=%~2

::echo raw_file_folder=%raw_file_folder%
::echo extracted_file_folder=%extracted_file_folder%

if not "%raw_file_folder%" == "" (
    IF not "%extracted_file_folder%" == "" (
        ::echo 1
        python qns_extraction.py -r "%raw_file_folder%" -e "%extracted_file_folder%"
        ::python -c "print()"
        ::python -c "print('Middle')"
        ::python -c "print()"
        python extracted_processing.py -e "%extracted_file_folder%"
    ) ELSE (
        ::echo 2
        python qns_extraction.py -r "%raw_file_folder%"
        ::python -c "print()"
        ::python -c "print('Middle')"
        ::python -c "print()"
        python extracted_processing.py
    )
) ELSE (
    if not "%extracted_file_folder%" == "" (
        ::echo 3
        python qns_extraction.py -e "%extracted_file_folder%"
        ::python -c "print()"
        ::python -c "print('Middle')"
        ::python -c "print()"
        python extracted_processing.py -e "%extracted_file_folder%"
    ) ELSE (
        ::echo 4
        python qns_extraction.py
        ::python -c "print()"
        ::python -c "print('Middle')"
        ::python -c "print()"
        python extracted_processing.py
    )
)   