
# Rename invalid enum names created by model generation
sed -i "" "s/_m___p___q_user__u_db__d_app__a_/m___p___q_user__u_db__d_app__a_/g" src/digitalocean/models.py
sed -i "" "s/_t___p_____l_1__user__u_db__d_app__a_client__h/t___p_____l_1__user__u_db__d_app__a_client__h/g" src/digitalocean/models.py 

# Symlink the aio/operations/_patch.py 
rm ./src/digitalocean/aio/operations/_patch.py
ln -s $PWD/src/digitalocean/operations/_patch.py ./src/digitalocean/aio/operations/_patch.py