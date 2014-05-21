Summary:     Percona Cluster Check
Name:        percona-clustercheck
Version:        1.0
Release:        0
License:        none
Source:         %{name}.tar.gz
BuildArch:      noarch
BuildRoot:      %{_tmppath}/%{name}-build
Requires:	python-twisted,MySQL-python
Group:          System/Base

%description
This package provides a python percona cluster health check interface

%prep
%setup -n %{name}

%build
# this section is empty as we're not actually building anything

%install
# create directories where the files will be located
mkdir -p $RPM_BUILD_ROOT/etc/init.d
mkdir -p $RPM_BUILD_ROOT/etc/sysconfig
mkdir -p $RPM_BUILD_ROOT/usr/sbin

# put the files in to the relevant directories.
install -m 755 etc/init.d/percona-clustercheck $RPM_BUILD_ROOT/etc/init.d/
install -m 755 etc/sysconfig/percona-clustercheck $RPM_BUILD_ROOT/etc/sysconfig/
install -m 755 usr/sbin/clustercheck.py $RPM_BUILD_ROOT/usr/sbin

%post
# the post section is where you can run commands after the rpm is installed.
/sbin/chkconfig percona-clustercheck on

%clean
rm -rf $RPM_BUILD_ROOT
rm -rf %{_tmppath}/%{name}
rm -rf %{_topdir}/BUILD/%{name}

%files
%defattr(-,root,root)
/etc/init.d/percona-clustercheck
/usr/sbin/clustercheck.py
%config /etc/sysconfig/percona-clustercheck

%changelog
* Wed May 21 2014  Todd Merritt <tmerritt@email.arizona.edu>
- 1.0 r1 First rpm build
