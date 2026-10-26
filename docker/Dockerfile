FROM ucmercedandeslab/tinyos:tossim

ENV TOSROOT=/opt/tinyos-main
ENV TINYOS_NO_DEPRECATION_WARNING=1

WORKDIR /opt/PSOClustering
COPY tinyos/ /opt/PSOClustering/


RUN make micaz sim


CMD ["python2", "run_tossim.py", "--rounds", "150", "--log", "tossim_run.log"]
