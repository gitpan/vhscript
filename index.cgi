#!/usr/bin/perl -U
# virtual hosting script v0.5 (c) Denis Kaganovich AKA mahatma
#
# redirect & compress by gzip on-the-fly multiple vhosts witheout real
# virtual hosts support on site. very simple!

### config begin
my $root=$ENV{DOCUMENT_ROOT}||'.';
my $mode=1; # 0-single, 1-www.doe.com-"doe/", 2-"www.doe.com/"
my $index=['index.htm','index.html'];
my $linkindex='index.cgi';
my $codepage='koi8-r';
my $enable_gzip=1;
my $vbase="$root/";
my $logs="$root/log/";
my $loglevel=1;
my $linktype=0; # 0-symlink; 1-dir; 2,3-internal (don't touch); for 2 must be absolute $vbase
my $cache=1; # cache .gz?
my $zbase="$root/cache/";
my $gzip='/usr/bin/gzip';
my $mkdir_mode=0770;
### config end

my %mime=(
'.html'=>'text/html',
'.htm'=>'text/html',
'.txt'=>'text/plain',
'.cgi'=>'text/plain',
'.js'=>'text/javascript',
#'js'=>'application/x-javascript',
'.gif'=>'image/gif',
'.jpg'=>'image/jpeg',
'.gz'=>'application/x-gzip'
);

my %mime_gz=( # -1
'Lynx'=>{
	'text/html'=>2,
	'text/plain'=>2,
	'*'=>1
}, # for Lynx gzip only text/html & text/plain
'*'=>{
	'image/jpeg'=>1,
	'*'=>2
} # for others compress all exclude jpeg
);

$enable_gzip=index($ENV{HTTP_ACCEPT_ENCODING},'gzip',0)>=0?$enable_gzip:0;
my $hthead='<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2//EN">';
my $iam=$ENV{SCRIPT_FILENAME};
my $i;
my $ndx='';
my $txt='';
my $p=$mode==0?'':lc($ENV{HTTP_HOST});
if($mode==1){
	$p=substr($p,4) if(index($p,'www.')==0);
	$p=substr($p,0,index($p,'.'));
}elsif($mode==0){chop($vbase) if(substr($vbase,-1)=='/')};
my $rs=$ENV{REDIRECT_STATUS}+0;
my $f=$ENV{REQUEST_URI};
my $log=$loglevel>0?localtime(time)." - $ENV{REMOTE_ADDR}:$ENV{REMOTE_PORT} ".($loglevel>1?$ENV{HTTP_X_FORWARDED_FOR}||'-':'')." $ENV{REQUEST_METHOD} $ENV{HTTP_HOST}$f".($loglevel>2?' '.($ENV{HTTP_REFERER}||'?'):''):'';
my @fs;
$i=index($f,'?'); $f=substr($f,0,$i) if($i>0);
my $ff="$vbase$p$f";
my $t;
if($rs==404&&-d $ff){$ff.='/';$f.='/'}
if(substr($f,-1) eq '/'){		
	for ($i=0;$i<scalar(@$index) && !(@fs=stat("$ff".($ndx=@$index[$i]))); $i++){};
	if(@fs){$f.=$ndx; $ff.=$ndx}
	else{
		$t='.html';
		chop($i) if(length($i=$f)>1);
		$txt.="$hthead\n<html><head><title>Index of $i</title></head><body><table width=100%><tr><th>Name</th><th>Size</th><th>Date</th><th>Description</th></tr>";
		opendir DH,$ff or err(404,"path not found");
		my @dir=readdir(DH);
		my @stat;
		for $i (@dir){
			@stat=stat("$ff$i");
			@fs=@stat if(@fs[9]<@stat[9]);
			$txt.="\n<tr><td><a href=\"$i\">$i</a></td><td>@stat[7]</td><td>".localtime(@stat[9])."</td><td>&nbsp;</td></tr>"
		}
		closedir DH;
		$txt.='</table></body></html>'
	}

}
$t=$t||lc(substr($f,$i=rindex($f,'.')));
my $zz=0;
if($enable_gzip==1 && $t eq '.gz'){
	my $j=rindex($f,'.',$i-1);
	$t=lc(substr($f,$j,$i-$j));
	$zz=1;
}
my $loc=$f;
@fs=@fs||stat($ff);
err(404,'not found!'.$ff) if(!@fs);
$i=my $m=$mime{$t}||'*/*';
my $a=$ENV{HTTP_USER_AGENT};
$log.=" \"$a\"" if($loglevel>3);
$a=substr($a,0,index($a,'/'));
$log.=" $a" if($loglevel>0 && $loglevel<4);
$m.="; codepage=$codepage" if($codepage ne '' && index($m,'text/')>=0);

if($enable_gzip==1){
my $fz="$zbase$p$f.gz";
my $z=$mime_gz{$a}||$mime_gz{'*'}||{'*'=>2};
$z=($z->{$i}||$z->{'*'}||2)-1;
if($z==1||$zz==1){
	if($zz==0){
	$loc.='.gz';
	if($cache==0){$ff=$txt eq ''?"$gzip -cfn9 $ff |":"|$gzip -cfn9"}
	else{
		my @fzs=stat($fz);
		if((@fzs[9]||-1)<@fs[9]){
			mklink($fz,4,length($zbase));
			if($txt eq ''){`$gzip -cfn9 $ff >$fz`}
			else{
				open FH, "|$gzip -cfn9 >$fz";
				print FH $txt;
				close(FH);
				$txt=''
			}
			@fzs=stat($fz)
		}
		@fs[7]=@fzs[7];
		$ff=$fz
	}
	}
	$m.="\nContent-Encoding: gzip" if($t ne '.tar');
}
}

$m="Content-Type: $m\nContent-Location: $loc\nLast-Modified: ".localtime(@fs[9])."\n\n";
$log.=" - $ff" if($loglevel>0);
if($txt ne '' && $ff eq ''){print "Content-Length: ",length($txt),"\n",$m,$txt}
else{
	open FH,$ff or err(404,'not found'); binmode FH;
	mklink("$root$f$ndx",$linktype,length($root)) if($rs==404||$rs==403);
	if($cache==0 && $txt ne ''){print $m;print FH $txt}
	else{print "Content-Length: ",@fs[7],"\n",$m,<FH>;close FH}
}

lexit(0);

#################################################
sub mklink{
my $r=shift||return 1;
my $lnk=shift; # 0-symlink; 1-dir; 2-dir w/o last; 3-experimental, not work now
my $i0=shift||0;
my ($i,$i1)=(0,0);
my $l=length($r);
my $rr;
while($i0<=$l){
	$i=index($r,'/',$i0);
	$i1=$i<0?$l:$i;
	$rr=substr($r,0,$i1);
	if($lnk==3||($lnk==0 && $i>=0)){symlink('.',$rr)}
	elsif($lnk==1 && $i<0 && substr($r,-1) eq '/'){symlink($iam,"$r$linkindex")}
	elsif($lnk==0||($lnk==1 && $i<0)){symlink($iam,$rr)}
	elsif($lnk>0 && $i>=0){mkdir($rr,$mkdir_mode)}
	$i0=$i1+1;
}
}

sub err{
my $e=shift;
my $t=shift;
print qq(Content-Type: text/html
Pragma: no-cache
Content-Location: /error/$e.html

$hthead
<html><head><title>$e - $t</title></head><body>
<center><b>Error $e</b><br>$ENV{REQUEST_URI}<br>$t</center>
</body></html>);
lexit($e); 
}

sub lexit{
my $e=shift;
if($loglevel>0){
open FL, ">>$logs$p.log" or die "log error";
print FL "$log - $e\n";
close FL;
}
exit($e);
}
