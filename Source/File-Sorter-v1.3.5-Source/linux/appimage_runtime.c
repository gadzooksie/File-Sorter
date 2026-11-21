#define _GNU_SOURCE
#define _XOPEN_SOURCE 700
#include <elf.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <errno.h>
#include <unistd.h>
#include <dirent.h>
#include <limits.h>
#include <ftw.h>
#include <signal.h>
#include <zlib.h>

#define META_MAX 8192
#define BLK_MAX 131072
static volatile sig_atomic_t active_child=0;
static void forward_signal(int sig){if(active_child>0)kill((pid_t)active_child,sig);}
static int fd=-1;
static unsigned long long sqoff;
static unsigned char *inode_table,*dir_table;
static unsigned int ibsize,dbsize;
static unsigned long long inode_start,dir_start;
static uint16_t u16(const void*p){const unsigned char*b=p;return b[0]|(b[1]<<8);}
static uint32_t u32(const void*p){const unsigned char*b=p;return (uint32_t)b[0]|((uint32_t)b[1]<<8)|((uint32_t)b[2]<<16)|((uint32_t)b[3]<<24);}
static uint64_t u64(const void*p){const unsigned char*b=p;return (uint64_t)u32(b)|((uint64_t)u32(b+4)<<32);}
static void fail(const char*s){fprintf(stderr,"File Sorter AppImage: %s (%s)\n",s,strerror(errno));exit(1);}
static void getbuf(void*buf,size_t n,uint64_t off){if(pread(fd,buf,n,(off_t)off)!=(ssize_t)n)fail("cannot read AppImage");}
static uint64_t find_payload(){
    Elf64_Ehdr h;getbuf(&h,sizeof(h),0);
    if(memcmp(h.e_ident,ELFMAG,4)||memcmp(h.e_ident+8,"AI\2",3)||h.e_ident[EI_CLASS]!=ELFCLASS64)fail("not an x86-64 type-2 AppImage");
    if(h.e_shnum==0||h.e_shentsize!=sizeof(Elf64_Shdr))fail("invalid ELF sections");
    Elf64_Shdr s;getbuf(&s,sizeof(s),h.e_shoff+(uint64_t)(h.e_shnum-1)*sizeof(s));
    uint64_t x=h.e_shoff+(uint64_t)h.e_shnum*sizeof(s),y=s.sh_offset+s.sh_size;
    return x>y?x:y;
}
static unsigned char* read_meta(uint64_t addr,unsigned int *size){
    unsigned char h[2];getbuf(h,2,sqoff+addr);
    unsigned int stored=u16(h)&0x7fff;
    if(!stored||stored>META_MAX)fail("invalid metadata size");
    unsigned char src[META_MAX];getbuf(src,stored,sqoff+addr+2);
    unsigned char*dest=calloc(1,META_MAX);
    if(!dest)fail("out of memory");
    if(u16(h)&0x8000){memcpy(dest,src,stored);*size=stored;}
    else {uLongf n=META_MAX;if(uncompress(dest,&n,src,stored)!=Z_OK){free(dest);fail("invalid compressed metadata");}*size=(unsigned int)n;}
    return dest;
}
static int unpack_node(uint16_t index,const char*base,const char*name,int depth){
    if(depth>20)fail("directory depth limit exceeded");
    if(strchr(name,'/')||!strcmp(name,".")||!strcmp(name,".."))fail("invalid filename");
    char target[PATH_MAX];if(snprintf(target,sizeof(target),"%s%s%s",base,*name?"/":"",name)>=(int)sizeof(target))fail("path too long");
    if((unsigned int)index+32>ibsize)fail("invalid inode offset");
    unsigned char *p=inode_table+index;
    unsigned int type=u16(p),mode=u16(p+2)&0777;
    if(type==1){
        if(mkdir(target,0700)!=0&&errno!=EEXIST)fail("mkdir failed");
        unsigned int size=u16(p+24), offset=u16(p+26);
        if(size>=4){
            unsigned int length=size-3,end=offset+length;
            if(end>dbsize)fail("invalid directory offset");
            unsigned int pos=offset;
            while(pos<end){
                if(pos+12>end)fail("truncated directory header");
                unsigned int count=u32(dir_table+pos)+1;
                unsigned int block=u32(dir_table+pos+4);
                pos+=12;
                if(block!=0||count>256)fail("unexpected directory record");
                for(unsigned int j=0;j<count;j++){
                    if(pos+8>end)fail("truncated directory entry");
                    unsigned int off=u16(dir_table+pos);
                    unsigned int nlen=u16(dir_table+pos+6)+1;
                    pos+=8;
                    if(!nlen||nlen>255||pos+nlen>end)fail("invalid directory filename length");
                    char child[256];memcpy(child,dir_table+pos,nlen);child[nlen]=0;pos+=nlen;
                    unpack_node(off,target,child,depth+1);
                }
            }
        }
        chmod(target,mode);
    } else if(type==2){
        unsigned int start=u32(p+16),frag=u32(p+20),filelen=u32(p+28);
        if(frag!=0xffffffff)fail("fragment unsupported");
        unsigned int blockcnt=(filelen+BLK_MAX-1)/BLK_MAX;
        if(index+32+blockcnt*4>ibsize)fail("invalid block sizes");
        int out=open(target,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);
        if(out<0)fail("cannot create AppImage output file");
        uint64_t off=start;
        unsigned int remaining=filelen;
        for(unsigned int j=0;j<blockcnt;j++){
            unsigned int sz=u32(p+32+4*j),stored=sz&0x00ffffff;
            if(!stored||stored>BLK_MAX){close(out);fail("invalid file block size");}
            unsigned char *src=malloc(stored),*raw=malloc(BLK_MAX);
            if(!src||!raw){close(out);fail("memory error");}
            getbuf(src,stored,sqoff+off);off+=stored;
            unsigned int expected=remaining>BLK_MAX?BLK_MAX:remaining;
            if(sz&0x01000000){if(stored!=expected)fail("bad raw block");memcpy(raw,src,stored);}
            else{uLongf un=expected;if(uncompress(raw,&un,src,stored)!=Z_OK||un!=expected)fail("bad compressed block");}
            if(write(out,raw,expected)!=(ssize_t)expected)fail("cannot write extracted file");
            free(src);free(raw);remaining-=expected;
        }
        if(close(out)!=0)fail("closing extracted file failed");
        chmod(target,mode);
    } else fail("unsupported inode type");
    return 0;
}
static int remove_callback(const char*path,const struct stat*st,int flag,struct FTW*tw){(void)st;(void)flag;(void)tw;return remove(path);}
static void erase_tree(const char*path){nftw(path,remove_callback,32,FTW_DEPTH|FTW_PHYS);}
int main(int argc,char**argv){
    char self[PATH_MAX];ssize_t got=readlink("/proc/self/exe",self,sizeof(self)-1);
    if(got<=0)fail("cannot find AppImage path");
    self[got]=0;
    fd=open(self,O_RDONLY|O_CLOEXEC);if(fd<0)fail("cannot open AppImage");
    sqoff=find_payload();
    if(argc>1&&!strcmp(argv[1],"--appimage-offset")){printf("%llu\n",sqoff);return 0;}
    unsigned char sb[96];getbuf(sb,sizeof(sb),sqoff);
    if(memcmp(sb,"hsqs",4)||u16(sb+28)!=4||u16(sb+30)!=0||u16(sb+20)!=1||u32(sb+12)!=BLK_MAX)fail("invalid SquashFS v4 payload");
    inode_start=u64(sb+64);dir_start=u64(sb+72);
    inode_table=read_meta(inode_start,&ibsize);
    dir_table=read_meta(dir_start,&dbsize);
    uint64_t root=u64(sb+32);
    if(root>>16)fail("unsupported inode block reference");
    int extract_only=argc>1&&!strcmp(argv[1],"--appimage-extract");
    char tmp[PATH_MAX];
    if(extract_only){if(!getcwd(tmp,sizeof(tmp)))fail("cannot resolve CWD");if(strlen(tmp)+16>=sizeof(tmp))fail("path too long");strcat(tmp,"/squashfs-root");if(mkdir(tmp,0700)<0&&errno!=EEXIST)fail("cannot create squashfs-root");}
    else {strcpy(tmp,"/tmp/.mount_FileSorterXXXXXX");if(!mkdtemp(tmp))fail("mkdtemp failed");}
    // Extract the root directory into the desired destination.
    unpack_node((uint16_t)root,tmp,"",0);
    char full[PATH_MAX];snprintf(full,sizeof(full),"%s",tmp);
    if(extract_only){printf("AppImage extracted to %s\n",full);return 0;}
    setenv("APPIMAGE",self,1);setenv("APPDIR",full,1);
    char app_run[PATH_MAX];snprintf(app_run,sizeof(app_run),"%s/AppRun",full);
    signal(SIGTERM,forward_signal);signal(SIGINT,forward_signal);
    pid_t pid=fork();if(pid<0)fail("fork failed");
    if(pid==0){char**args=calloc((size_t)argc+1,sizeof(char*));if(!args)_exit(127);args[0]=app_run;for(int j=1;j<argc;j++)args[j]=argv[j];args[argc]=NULL;execv(app_run,args);perror("AppRun execv");_exit(127);}
    active_child=pid;
    int status=0;while(waitpid(pid,&status,0)<0){if(errno!=EINTR){status=127<<8;break;}}
    active_child=0;
    erase_tree(tmp);
    close(fd);free(inode_table);free(dir_table);
    if(WIFEXITED(status))return WEXITSTATUS(status);
    if(WIFSIGNALED(status))return 128+WTERMSIG(status);
    return 1;
}
