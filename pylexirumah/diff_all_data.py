import sys
import pandas
import check_consistency

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1] == "fix":
        check_consistency.on_error = check_consistency.warn
    else:
        check_consistency.on_error = check_consistency.error
    all_data = check_consistency.main()
    all_data.set_index(["Source", "Feature_ID", "Language_ID"], inplace=True)
    all_data_saved = pandas.io.parsers.read_csv(
        "all_data.tsv",
        index_col=["Source", "Feature_ID", "Language_ID"],
        sep="\t",
        encoding='utf-16')
    print()
    try:
        changed_lines = (all_data_saved.fillna("") != all_data.fillna("")).any(1)
    except ValueError:
        print("Special all_data.tsv entries:")
        print(all_data_saved["Counterpart"][all_data_saved.index.difference(all_data.index)])
        print("Special entries in other files:")
        print(all_data_saved["Counterpart"][all_data.index.difference(all_data_saved.index)])
        check_consistency.on_error("Word lists have changed!")
        changed_lines = (
            all_data_saved.loc[all_data_saved.index.intersection(all_data.index)].fillna("")
            != all_data.loc[all_data_saved.index.intersection(all_data.index)].fillna("")).any(1)
    if changed_lines.any():
        old = all_data[changed_lines]
        new = all_data_saved[changed_lines]
        print("CHANGES DETECTED:")
        print(old.to_string())
        print("->")
        print(new.to_string())
        if check_consistency.on_error == check_consistency.warn:
            check_consistency.warn("Some data has been changed in all_changes…")
            for source in new.index.get_level_values('Source'):
                all_data_saved.loc[source].to_csv(
                    source,
                    sep="\t",
                    encoding='utf-16')
    else:
        print("NO CHANGES DETECTED")
