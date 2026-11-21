#ifndef SORTER_UPDATE_H
#define SORTER_UPDATE_H
/* Shared lightweight update integration for File Sorter X11 clients.
 * Define UPDATE_NOTIFY(message) before including this header.
 * The installed Sorter.Updater helper uses Python 3's standard library.
 */
#ifndef UPDATE_NOTIFY
#error "Define UPDATE_NOTIFY(message) before including sorter_update.h"
#endif

static char su_config[PATH_MAX],su_app_dir[PATH_MAX];
#include "sorter_updater_embedded.h"
static int su_auto_enabled=1,su_fd=-1;
static pid_t su_pid=-1;
static char su_line[512];
static size_t su_line_len=0;

static int su_mkdir_dir(const char *name){
    struct stat st;
    if(mkdir(name,0700)==0)return 0;
    return errno==EEXIST && lstat(name,&st)==0 && S_ISDIR(st.st_mode) ? 0:-1;
}
static void su_copy_legacy_file(const char *source,const char *dest){
    struct stat st;
    int input=open(source,O_RDONLY|O_NOFOLLOW|O_CLOEXEC);
    if(input<0)return;
    if(fstat(input,&st)!=0 || !S_ISREG(st.st_mode) || st.st_size>1024*1024){close(input);return;}
    int output=open(dest,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);
    if(output<0){close(input);return;}
    char buf[8192];int ok=1;ssize_t got;
    while((got=read(input,buf,sizeof(buf)))>0){ssize_t pos=0;
        while(pos<got){ssize_t wrote=write(output,buf+pos,(size_t)(got-pos));
            if(wrote<0 && errno==EINTR)continue;
            if(wrote<=0){ok=0;break;}pos+=wrote;
        }
        if(!ok)break;
    }
    if(got<0)ok=0;
    if(fsync(output)!=0)ok=0;
    close(input);close(output);
    if(!ok)unlink(dest);
}
static void su_initialize(void){
    const char *home=getenv("HOME"),*xdg=getenv("XDG_CONFIG_HOME");
    char parent[PATH_MAX],older[PATH_MAX],old_file[PATH_MAX],new_file[PATH_MAX];
    if(!home || home[0]!='/')return;
    if(xdg && xdg[0]=='/')snprintf(parent,sizeof(parent),"%s",xdg);
    else snprintf(parent,sizeof(parent),"%s/.config",home);
    if(snprintf(su_config,sizeof(su_config),"%s/sorter-config",parent)>=(int)sizeof(su_config))return;
    if(snprintf(older,sizeof(older),"%s/general-cleanup-gui",parent)>=(int)sizeof(older))return;
    if(su_mkdir_dir(parent)==0 && su_mkdir_dir(su_config)==0){
        struct stat st;
        if(lstat(older,&st)==0 && S_ISDIR(st.st_mode)){
            const char *files[]={"directories.txt","rules.tsv","auto-update.txt"};
            for(size_t i=0;i<sizeof(files)/sizeof(files[0]);i++){
                if(snprintf(old_file,sizeof(old_file),"%s/%s",older,files[i])>=(int)sizeof(old_file))continue;
                if(snprintf(new_file,sizeof(new_file),"%s/%s",su_config,files[i])>=(int)sizeof(new_file))continue;
                su_copy_legacy_file(old_file,new_file);
            }
        }
    }
    if(snprintf(new_file,sizeof(new_file),"%s/auto-update.txt",su_config)<(int)sizeof(new_file)){
        FILE *f=fopen(new_file,"r");
        if(f){char value[32]={0};if(fgets(value,sizeof(value),f))su_auto_enabled=strncmp(value,"off",3)!=0;fclose(f);}
    }
    char exe[PATH_MAX];ssize_t len=readlink("/proc/self/exe",exe,sizeof(exe)-1);
    if(len>0){exe[len]=0;char *slash=strrchr(exe,'/');if(slash){*slash=0;snprintf(su_app_dir,sizeof(su_app_dir),"%s",exe);
    }}
}
static void su_toggle_auto(void){
    char path[PATH_MAX];if(!*su_config || snprintf(path,sizeof(path),"%s/auto-update.txt",su_config)>=(int)sizeof(path))return;
    FILE *f=fopen(path,"w");if(!f){UPDATE_NOTIFY("Could not save auto-update setting.");return;}
    fputs(su_auto_enabled?"off\n":"on\n",f);
    if(fclose(f)!=0){UPDATE_NOTIFY("Could not save auto-update setting.");return;}
    su_auto_enabled=!su_auto_enabled;
    UPDATE_NOTIFY(su_auto_enabled?"Automatic updates enabled.":"Automatic updates disabled.");
}
static void su_launch(int automatic){
    if(su_pid>0){if(!automatic)UPDATE_NOTIFY("An update check is already running.");return;}
    if(!*su_app_dir){
        if(!automatic)UPDATE_NOTIFY("Could not find the application installation folder.");
        return;
    }
    int pipefd[2];if(pipe(pipefd)<0){if(!automatic)UPDATE_NOTIFY("Could not start update checker.");return;}
    pid_t child=fork();if(child<0){close(pipefd[0]);close(pipefd[1]);return;}
    if(child==0){
        close(pipefd[0]);dup2(pipefd[1],STDOUT_FILENO);dup2(pipefd[1],STDERR_FILENO);close(pipefd[1]);
        /* The GUI uses its own built-in v1.3.5 updater to prevent stale external
           Sorter.Updater helpers from breaking ZIP-based GitHub releases. */
        const char *appimage=getenv("APPIMAGE");
        if(appimage && appimage[0]=='/'){
            char *argv[]={"python3","-c",(char*)su_embedded_updater,"--appimage",(char*)appimage,
                          automatic?"--auto":"--install",NULL};
            execvp("python3",argv);
        }else{
            char *argv[]={"python3","-c",(char*)su_embedded_updater,"--app-dir",su_app_dir,
                          automatic?"--auto":"--install",NULL};
            execvp("python3",argv);
        }
        dprintf(STDERR_FILENO,"Update error: Python 3 is required (%s).\n",strerror(errno));
        _exit(127);
    }
    close(pipefd[1]);su_fd=pipefd[0];
    int f=fcntl(su_fd,F_GETFL);if(f>=0)fcntl(su_fd,F_SETFL,f|O_NONBLOCK);
    su_pid=child;su_line_len=0;
    if(!automatic)UPDATE_NOTIFY("Checking latest GitHub release and updating if needed...");
}
static void su_poll(void){
    if(su_pid<=0)return;
    if(su_fd>=0){char buf[1024];ssize_t got;
        while((got=read(su_fd,buf,sizeof(buf)))>0){for(ssize_t i=0;i<got;i++){
            unsigned char c=(unsigned char)buf[i];
            if(c=='\n'){
                if(su_line_len){su_line[su_line_len]=0;UPDATE_NOTIFY(su_line);su_line_len=0;}
            }else if(c>=32 && c<127 && su_line_len<sizeof(su_line)-1){su_line[su_line_len++]=(char)c;}
        }}
        if(got==0){close(su_fd);su_fd=-1;}
    }
    int status=0;pid_t finished=waitpid(su_pid,&status,WNOHANG);
    if(finished==su_pid){
        if(su_line_len){su_line[su_line_len]=0;UPDATE_NOTIFY(su_line);su_line_len=0;}
        if(!(WIFEXITED(status)&&WEXITSTATUS(status)==0))UPDATE_NOTIFY("Update check failed. See the error above.");
        if(su_fd>=0){close(su_fd);su_fd=-1;}
        su_pid=-1;
    }
}
static void su_cleanup(void){
    if(su_fd>=0)close(su_fd);
    /* Updater can finish after the GUI exits; its own lock protects concurrent runs. */
}
#endif
