

conda env export -n base > base_environment.yml

recreate environment 
#conda env create -f environment.yml


#save package list
#conda list --export > package-list.txt

#recreate from list
#conda create -n newenv --file package-list.txt
